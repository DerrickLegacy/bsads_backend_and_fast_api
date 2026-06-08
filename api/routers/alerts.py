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


def _safe_advisory(alert: Alert) -> Advisory | None:
    """Load linked advisory without joinedload (avoids broken join paths on some DBs)."""
    try:
        return alert.advisory
    except Exception:
        return None


def _to_mobile(alert: Alert, index: int = 0) -> MobileAlertResponse:
    advisory = _safe_advisory(alert)
    title = (
        advisory.condition_label
        if advisory and advisory.condition_label
        else (alert.recommended_action or "Alert")
    )
    return MobileAlertResponse(
        id=str(alert.alert_id),
        hive_id=str(alert.hive_id),
        severity=alert.severity_level or "info",
        title=title,
        date=alert.alert_timestamp.isoformat() if alert.alert_timestamp else "",
        summary=alert.recommended_action or "",
    )


def _to_mobile_detail(alert: Alert) -> MobileAlertDetailResponse:
    from api.models import AudioSource, InferenceResult
    from api.database import SessionLocal
    
    advisory_obj = _safe_advisory(alert)
    title = (
        advisory_obj.condition_label
        if advisory_obj and advisory_obj.condition_label
        else (alert.recommended_action or "Alert")
    )
    details = (
        advisory_obj.advisory_text
        if advisory_obj and advisory_obj.advisory_text
        else (alert.recommended_action or "")
    )
    
    # Get the hive name
    db = SessionLocal()
    try:
        hive = db.query(Hive).filter(Hive.hive_id == alert.hive_id).first()
        hive_name = hive.hive_name if hive else None
    finally:
        db.close()
    
    # Get audio recording if available
    audio_recording = None
    if alert.inference_id:
        db = SessionLocal()
        try:
            inference = db.query(InferenceResult).filter(
                InferenceResult.inference_id == alert.inference_id
            ).first()
            
            if inference and inference.audio_id:
                audio = db.query(AudioSource).filter(
                    AudioSource.audio_id == inference.audio_id
                ).first()
                
                if audio:
                    audio_recording = {
                        "id": str(audio.audio_id),
                        "file_path": audio.source_url,  # source_url is the path to the audio file
                        "duration_seconds": int(audio.duration_seconds) if audio.duration_seconds else 30,
                        "recorded_at": audio.captured_at.isoformat() if audio.captured_at else "",
                    }
        finally:
            db.close()
    
    # Build advisory detail if available
    advisory_detail = None
    if advisory_obj:
        advisory_detail = {
            "id": str(advisory_obj.advisory_id),
            "alert_id": str(alert.alert_id),
            "type": advisory_obj.advisory_type,
            "summary": advisory_obj.advisory_text or "",
            "actions": [
                {
                    "id": str(action.action_id),
                    "description": action.action_description,
                    "priority": action.priority_level.capitalize(),  # Ensure proper case: "High", "Medium", "Low"
                }
                for action in advisory_obj.actions
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
    )


@mobile_alerts_router.get("", response_model=list[MobileAlertResponse])
def get_all_alerts(
    hive_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return alerts.
    - Admin: all alerts system-wide (optionally filtered by ?hive_id=).
    - Farmer/mobile: only their own hives' alerts.
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

    alerts = q.order_by(Alert.alert_timestamp.desc()).limit(100).all()
    return [_to_mobile(a, i) for i, a in enumerate(alerts)]


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

    return _to_mobile_detail(alert)


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

    # Automatically acknowledge when viewing details (if still pending)
    if alert.action_status == "pending":
        alert.action_status = "acknowledged"
        db.commit()
        db.refresh(alert)

    return _to_mobile_detail(alert)


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

    advisory = _safe_advisory(alert)
    if not advisory:
        raise HTTPException(status_code=404, detail="No advisory linked to this alert")

    return AdvisoryResponse.model_validate(advisory)


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

    return _to_mobile_detail(alert)
