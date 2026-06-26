from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Alert, Advisory, Hive, User
from api.routers.auth import get_current_user
from api.schemas import AdvisoryResponse, AlertResponse, MobileAlertDetailResponse, MobileAlertResponse

# ---------------------------------------------------------------------------
# Per-hive alert routes  (used by web admin panel)
# ---------------------------------------------------------------------------
hive_alerts_router = APIRouter(prefix="/hives", tags=["Alerts"])


@hive_alerts_router.get("/{hive_id}/alerts", response_model=list[AlertResponse])
def get_hive_alerts(
    hive_id: str,
    only_pending: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return alerts for a specific hive.
    Returns an empty list [] if no alerts exist — never 404 on missing alerts.
    Pass ?only_pending=true to filter to unacknowledged alerts only.
    Admin can access any hive; farmers can only access their own.
    """
    q = db.query(Hive).filter(Hive.hive_id == hive_id, Hive.is_deleted == False)
    if current_user.role != "admin":
        q = q.filter(Hive.owner_id == current_user.user_id)

    hive = q.first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    query = db.query(Alert).filter(Alert.hive_id == hive_id)
    if only_pending:
        query = query.filter(Alert.action_status == "pending")

    return query.order_by(Alert.alert_timestamp.desc()).all()


@hive_alerts_router.get("/{hive_id}/alerts/debug", tags=["Debug"])
def debug_hive_alerts(
    hive_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Debug endpoint to check why alerts might be empty for a hive.
    Returns information about the hive, its inferences, and alerts.
    """
    from api.models import InferenceResult
    
    q = db.query(Hive).filter(Hive.hive_id == hive_id, Hive.is_deleted == False)
    if current_user.role != "admin":
        q = q.filter(Hive.owner_id == current_user.user_id)

    hive = q.first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    # Count all alerts for this hive
    total_alerts = db.query(Alert).filter(Alert.hive_id == hive_id).count()
    pending_alerts = db.query(Alert).filter(
        Alert.hive_id == hive_id,
        Alert.action_status == "pending"
    ).count()
    
    # Count inferences
    total_inferences = db.query(InferenceResult).filter(
        InferenceResult.hive_id == hive_id
    ).count()
    
    # Get latest inference
    latest_inference = db.query(InferenceResult).filter(
        InferenceResult.hive_id == hive_id
    ).order_by(InferenceResult.analyzed_at.desc()).first()
    
    # Get latest alert
    latest_alert = db.query(Alert).filter(
        Alert.hive_id == hive_id
    ).order_by(Alert.alert_timestamp.desc()).first()
    
    return {
        "hive_id": str(hive_id),
        "hive_name": hive.hive_name,
        "hive_state": hive.current_state,
        "total_alerts": total_alerts,
        "pending_alerts": pending_alerts,
        "total_inferences": total_inferences,
        "latest_inference": {
            "inference_id": str(latest_inference.inference_id),
            "hive_state": latest_inference.hive_state,
            "confidence_score": float(latest_inference.confidence_score),
            "analyzed_at": latest_inference.analyzed_at.isoformat() if latest_inference.analyzed_at else None,
        } if latest_inference else None,
        "latest_alert": {
            "alert_id": str(latest_alert.alert_id),
            "severity_level": latest_alert.severity_level,
            "action_status": latest_alert.action_status,
            "recommended_action": latest_alert.recommended_action,
            "alert_timestamp": latest_alert.alert_timestamp.isoformat() if latest_alert.alert_timestamp else None,
        } if latest_alert else None,
        "explanation": (
            "No alerts exist for this hive yet. Alerts are created when audio recordings are analyzed "
            "and the inference engine detects conditions that require farmer attention (e.g., swarming, "
            "queenless, pest infestation). Make sure audio recordings are being uploaded and processed."
        ) if total_alerts == 0 else (
            f"This hive has {total_alerts} total alerts, {pending_alerts} pending. "
            "Alerts may be empty on the mobile screen if they have all been acknowledged."
        )
    }


@hive_alerts_router.patch("/{hive_id}/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_hive_alert(
    hive_id: str,
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an alert as acknowledged — farmer has seen and acted on it."""
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.owner_id == current_user.user_id,
    ).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    alert = db.query(Alert).filter(
        Alert.alert_id == alert_id,
        Alert.hive_id == hive_id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.action_status = "acknowledged"
    db.commit()
    db.refresh(alert)
    return alert


# ---------------------------------------------------------------------------
# Top-level alert routes  (consumed by the mobile app)
# ---------------------------------------------------------------------------
mobile_alerts_router = APIRouter(prefix="/alerts", tags=["Mobile Alerts"])


def _safe_advisory(alert: Alert, db: Session) -> Advisory | None:
    """Load linked advisory through inference → advisory_actions path."""
    try:
        # Alert → InferenceResult → AdvisoryActions → Advisory
        from api.models import AdvisoryAction, InferenceResult
        if not alert.inference_id:
            return None
        
        # Get the first advisory action for this inference (highest priority)
        action = (
            db.query(AdvisoryAction)
            .filter(AdvisoryAction.inference_id == alert.inference_id)
            .order_by(AdvisoryAction.priority_level.desc(), AdvisoryAction.created_at.asc())
            .first()
        )
        
        if action and action.advisory:
            return action.advisory
        return None
    except Exception:
        return None


def _to_mobile(alert: Alert, db: Session, index: int = 0) -> MobileAlertResponse:
    from api.models import AdvisoryAction, AdvisoryTemplate, InferenceResult
    
    # Get inference to find the hive state
    title = "Alert"
    if alert.inference_id:
        inference = db.query(InferenceResult).filter(
            InferenceResult.inference_id == alert.inference_id
        ).first()
        
        if inference:
            # Get template for better title
            action = db.query(AdvisoryAction).filter(
                AdvisoryAction.inference_id == alert.inference_id
            ).first()
            
            if action:
                template = db.query(AdvisoryTemplate).filter(
                    AdvisoryTemplate.template_id == action.template_id
                ).first()
                
                if template:
                    # Format the hive state as a readable title
                    title = template.hive_state.replace("_", " ").title()
                else:
                    title = inference.hive_state.replace("_", " ").title()
            else:
                title = inference.hive_state.replace("_", " ").title()
    
    # Use recommended_action as summary if available
    summary = alert.recommended_action or "Tap to view details"
    
    return MobileAlertResponse(
        id=str(alert.alert_id),
        hive_id=str(alert.hive_id),
        severity=alert.severity_level or "info",
        title=title,
        date=alert.alert_timestamp.isoformat() if alert.alert_timestamp else "",
        summary=summary,
        alertStatus=alert.action_status or "pending",
        viewed_at=alert.viewed_at.isoformat() if alert.viewed_at else None,
    )


def _to_mobile_detail(alert: Alert, db: Session) -> MobileAlertDetailResponse:
    from api.models import AdvisoryAction, AdvisoryTemplate, AudioSource, InferenceResult
    
    # Get the hive name
    hive = db.query(Hive).filter(Hive.hive_id == alert.hive_id).first()
    hive_name = hive.hive_name if hive else None
    
    # Get inference result for prediction details
    inference = None
    prediction_details = None
    
    # Get audio recording if available
    audio_recording = None
    if alert.inference_id:
        inference = db.query(InferenceResult).filter(
            InferenceResult.inference_id == alert.inference_id
        ).first()
        
        # Extract prediction details from inference
        if inference and inference.prediction_details:
            prediction_details = inference.prediction_details
        
        if inference and inference.audio_id:
            audio = db.query(AudioSource).filter(
                AudioSource.audio_id == inference.audio_id
            ).first()
            
            if audio:
                # Use the backend stream endpoint instead of direct farmer server URL
                # This allows the mobile app to play audio without auth issues
                from api.config import settings
                stream_url = f"/audio/{audio.audio_id}/stream"
                
                audio_recording = {
                    "id": str(audio.audio_id),
                    "file_path": stream_url,  # Use backend stream URL
                    "duration_seconds": int(audio.duration_seconds) if audio.duration_seconds else 30,
                    "recorded_at": audio.captured_at.isoformat() if audio.captured_at else "",
                }
    
    # Get all AdvisoryAction records for this inference (these are the inference-specific actions)
    advisory_actions = []
    template = None
    if alert.inference_id:
        # Order by priority: high → medium → low
        # Use CASE to convert priority strings to numbers for proper ordering
        from sqlalchemy import case
        priority_order = case(
            (AdvisoryAction.priority_level == "high", 1),
            (AdvisoryAction.priority_level == "medium", 2),
            (AdvisoryAction.priority_level == "low", 3),
            else_=4
        )
        advisory_actions = db.query(AdvisoryAction).filter(
            AdvisoryAction.inference_id == alert.inference_id
        ).order_by(
            priority_order,
            AdvisoryAction.created_at
        ).all()
        
        # Get the template from the first action if available
        if advisory_actions:
            template = db.query(AdvisoryTemplate).filter(
                AdvisoryTemplate.template_id == advisory_actions[0].template_id
            ).first()
    
    # Get title and details from template or alert
    if template:
        # Use human-readable title from hive_state, details from admin-configured description
        title = template.hive_state.replace("_", " ").title()
        details = template.description or alert.recommended_action or ""
        advisory_type = template.advisory_type
    else:
        title = alert.recommended_action or "Alert"
        details = alert.recommended_action or ""
        advisory_type = "Reactive"
    
    # Build advisory detail with all the inference-specific actions
    advisory_detail = None
    if advisory_actions:
        advisory_detail = {
            "id": str(advisory_actions[0].advisory_id) if advisory_actions else "",
            "alert_id": str(alert.alert_id),
            "type": advisory_type,
            "summary": details,
            "actions": [
                {
                    "id": str(action.action_id),
                    "title": action.action_title,
                    "description": action.action_description,
                    "priority": action.priority_level.capitalize(),
                }
                for action in advisory_actions
            ],
        }
    
    return MobileAlertDetailResponse(
        id=str(alert.alert_id),
        hive_id=str(alert.hive_id),
        hive_name=hive_name,
        severity=alert.severity_level or "info",
        title=title,
        time=alert.alert_timestamp.isoformat() if alert.alert_timestamp else "",
        created_at=alert.alert_timestamp.isoformat() if alert.alert_timestamp else "",
        details=details,
        acknowledged=alert.action_status == "acknowledged",
        audio_recording=audio_recording,
        advisory=advisory_detail,
        prediction_details=prediction_details,  # Include ML model predictions
    )


@mobile_alerts_router.get("", response_model=list[MobileAlertResponse])
def get_all_alerts(
    hive_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return alerts for display in the mobile app.
    - Admin: all alerts system-wide (optionally filtered by ?hive_id=).
    - Farmer/mobile: only their own hives' alerts.
    
    Returns alerts ordered by newest first with proper notification data.
    """
    if current_user.role != "admin":
        hive_ids = [
            str(row.hive_id)
            for row in db.query(Hive.hive_id)
            .filter(Hive.owner_id == str(current_user.user_id))
            .all()
        ]
        if not hive_ids:
            return []

    q = db.query(Alert)

    if current_user.role == "admin":
        if hive_id:
            q = q.filter(Alert.hive_id == hive_id)
    else:
        q = q.filter(Alert.hive_id.in_(hive_ids))
        if hive_id:
            q = q.filter(Alert.hive_id == hive_id)

    alerts = q.order_by(Alert.alert_timestamp.desc()).limit(10).all()
    return [_to_mobile(a, db, i) for i, a in enumerate(alerts)]


@mobile_alerts_router.patch("/{alert_id}/notify", response_model=MobileAlertDetailResponse)
def notify_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an alert as 'sent' (notification dispatched). Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.action_status = "sent"
    db.commit()
    db.refresh(alert)

    return _to_mobile_detail(alert, db)


@mobile_alerts_router.get("/{alert_id}", response_model=MobileAlertDetailResponse)
def get_alert_detail(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the detail of a single alert (mobile alert detail screen).
    Automatically marks the alert as acknowledged when viewed.
    """
    hive_ids = [
        str(row.hive_id)
        for row in db.query(Hive.hive_id)
        .filter(Hive.owner_id == str(current_user.user_id))
        .all()
    ]

    if not hive_ids:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert = (
        db.query(Alert)
        .filter(Alert.alert_id == alert_id, Alert.hive_id.in_(hive_ids))
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Mark as viewed (sets viewed_at timestamp) but do NOT auto-acknowledge.
    # The farmer's badge count uses viewed_at to determine "seen" alerts.
    if alert.viewed_at is None:
        alert.viewed_at = datetime.utcnow()
        db.commit()
        db.refresh(alert)

    return _to_mobile_detail(alert, db)


@mobile_alerts_router.get("/{alert_id}/advisory", response_model=AdvisoryResponse)
def get_alert_advisory(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the advisory linked to a specific alert.

    The advisory contains the condition label, advisory text, severity, and
    any associated action checklist items generated by the inference engine.

    Returns 404 if the alert does not exist or does not belong to the current
    user's hives. Returns 404 if the alert exists but has no advisory yet.
    """
    # Scope to the current user's hives (admin can see all)
    if current_user.role == "admin":
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    else:
        hive_ids = [
            str(row.hive_id)
            for row in db.query(Hive.hive_id)
            .filter(Hive.owner_id == str(current_user.user_id))
            .all()
        ]
        if not hive_ids:
            raise HTTPException(status_code=404, detail="Alert not found")
        alert = (
            db.query(Alert)
            .filter(Alert.alert_id == alert_id, Alert.hive_id.in_(hive_ids))
            .first()
        )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    advisory = _safe_advisory(alert, db)
    if not advisory:
        raise HTTPException(status_code=404, detail="No advisory linked to this alert")

    # Build response from Advisory and its template
    template = advisory.template
    return AdvisoryResponse(
        advisory_id=str(advisory.advisory_id),
        advisory_type=template.advisory_type if template else "Reactive",
        condition_label=template.hive_state if template else None,
        advisory_text=advisory.action_description,
        severity=template.severity if template else "info",
        actions=[
            AdvisoryActionResponse(
                action_id=str(action.action_id),
                action_description=action.action_description,
                priority_level=action.priority_level,
                status=action.status
            )
            for action in advisory.actions
        ]
    )


@mobile_alerts_router.post("/{alert_id}/acknowledge", response_model=MobileAlertDetailResponse)
def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an alert from the mobile app."""
    hive_ids = [
        str(row.hive_id)
        for row in db.query(Hive.hive_id)
        .filter(Hive.owner_id == str(current_user.user_id))
        .all()
    ]

    if not hive_ids:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert = (
        db.query(Alert)
        .filter(Alert.alert_id == alert_id, Alert.hive_id.in_(hive_ids))
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.action_status = "acknowledged"
    db.commit()
    db.refresh(alert)

    return _to_mobile_detail(alert, db)
