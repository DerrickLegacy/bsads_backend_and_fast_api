"""
Top-level read endpoints for inferences and advisories.
Admin sees all records; farmers see only their own hives' records.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.database import get_db
from api.models import Advisory, AdvisoryAction, AdvisoryTemplate, FarmerDataSource, Hive, InferenceResult, User
from api.routers.auth import get_current_user
from api.schemas import AdvisoryResponse, AdvisoryActionResponse, AdminAdvisoryResponse, InferenceResponse, AlertResponse

router = APIRouter(tags=["Inferences & Advisories"])


def _hive_ids_for(user: User, db: Session) -> list[str] | None:
    """Return hive_id list for non-admin, or None meaning 'all hives'."""
    if user.role == "admin":
        return None
    return [r.hive_id for r in db.query(Hive.hive_id).filter(Hive.owner_id == user.user_id).all()]


def _build_inference_response(inference: InferenceResult, db: Session) -> InferenceResponse:
    """
    Build InferenceResponse with manually constructed advisory data.
    The advisory field comes from advisory_actions → advisory → template path.
    """
    # Get alert data
    alert_data = None
    if inference.alert:
        alert_data = AlertResponse(
            alert_id=str(inference.alert.alert_id),
            hive_id=str(inference.alert.hive_id),
            severity_level=inference.alert.severity_level,
            recommended_action=inference.alert.recommended_action,
            action_status=inference.alert.action_status,
            alert_timestamp=inference.alert.alert_timestamp
        )
    
    # Get advisory data from advisory_actions
    advisory_data = None
    if inference.advisory_actions:
        # Get the first advisory action to build the advisory response
        first_action = inference.advisory_actions[0]
        if first_action.advisory:
            advisory = first_action.advisory
            template = advisory.template
            
            # Build advisory response from Advisory and Template
            advisory_data = AdvisoryResponse(
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
                    for action in inference.advisory_actions
                ]
            )
    
    return InferenceResponse(
        inference_id=str(inference.inference_id),
        hive_id=str(inference.hive_id),
        hive_state=inference.hive_state,
        confidence_score=float(inference.confidence_score),
        inference_latency_ms=int(inference.inference_latency_ms) if inference.inference_latency_ms else None,
        created_at=inference.created_at,
        alert=alert_data,
        advisory=advisory_data
    )


# ---------------------------------------------------------------------------
# Inferences
# ---------------------------------------------------------------------------
@router.get("/inferences", response_model=list[InferenceResponse])
def list_inferences(
    hive_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All inference results. Admin sees everything; farmers see their own hives."""
    allowed_ids = _hive_ids_for(current_user, db)

    q = (
        db.query(InferenceResult)
        .options(
            joinedload(InferenceResult.alert),
            joinedload(InferenceResult.advisory_actions),
        )
    )

    if hive_id:
        # If farmer, validate they own this hive
        if allowed_ids is not None and hive_id not in allowed_ids:
            raise HTTPException(status_code=403, detail="Access denied")
        q = q.filter(InferenceResult.hive_id == hive_id)
    elif allowed_ids is not None:
        q = q.filter(InferenceResult.hive_id.in_(allowed_ids))

    results = q.order_by(InferenceResult.created_at.desc()).limit(limit).all()
    
    # Manually construct responses with advisory data
    return [_build_inference_response(r, db) for r in results]


@router.get("/inferences/{inference_id}", response_model=InferenceResponse)
def get_inference(
    inference_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_ids = _hive_ids_for(current_user, db)

    result = (
        db.query(InferenceResult)
        .options(
            joinedload(InferenceResult.alert),
            joinedload(InferenceResult.advisory_actions),
        )
        .filter(InferenceResult.inference_id == inference_id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Inference not found")

    if allowed_ids is not None and result.hive_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Access denied")

    return _build_inference_response(result, db)


# ---------------------------------------------------------------------------
# Advisories
# ---------------------------------------------------------------------------
@router.get("/advisories", response_model=list[AdminAdvisoryResponse])
def list_advisories(
    hive_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All generated advisories. Admin sees everything; farmers see their own."""
    allowed_ids = _hive_ids_for(current_user, db)

    q = db.query(Advisory)

    if hive_id:
        if allowed_ids is not None and hive_id not in allowed_ids:
            raise HTTPException(status_code=403, detail="Access denied")
        q = q.filter(Advisory.hive_id == hive_id)
    elif allowed_ids is not None:
        q = q.filter(Advisory.hive_id.in_(allowed_ids))

    return q.order_by(Advisory.created_at.desc()).limit(limit).all()


@router.get("/advisories/{advisory_id}", response_model=AdminAdvisoryResponse)
def get_advisory(
    advisory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_ids = _hive_ids_for(current_user, db)

    advisory = db.query(Advisory).filter(Advisory.advisory_id == advisory_id).first()
    if not advisory:
        raise HTTPException(status_code=404, detail="Advisory not found")

    if allowed_ids is not None and advisory.hive_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Access denied")

    return advisory


# ---------------------------------------------------------------------------
# Data Source Diagnostics (Admin Only)
# ---------------------------------------------------------------------------
@router.get("/admin/data-sources/status")
def get_data_sources_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Admin-only endpoint to diagnose data source connection issues.
    
    Returns all active data sources with their connection status,
    recent errors, and configuration details.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    sources = (
        db.query(FarmerDataSource)
        .join(Hive, FarmerDataSource.hive_id == Hive.hive_id)
        .join(User, FarmerDataSource.user_id == User.user_id)
        .filter(FarmerDataSource.is_active == True)
        .all()
    )
    
    result = []
    for source in sources:
        hive = db.query(Hive).filter(Hive.hive_id == source.hive_id).first()
        user = db.query(User).filter(User.user_id == source.user_id).first()
        
        api_url = None
        has_api_key = False
        
        if source.connection_config:
            api_url = source.connection_config.get("api_base_url")
            has_api_key = bool(source.connection_config.get("api_key"))
        
        # Check if this source has recent errors
        has_recent_errors = False
        if source.last_error_at:
            from datetime import datetime, timedelta
            time_since_error = datetime.utcnow() - source.last_error_at
            has_recent_errors = time_since_error < timedelta(hours=1)
        
        result.append({
            "source_id": str(source.source_id),
            "hive_id": str(source.hive_id),
            "hive_name": hive.hive_name if hive else None,
            "farmer_email": user.email if user else None,
            "source_type": source.source_type,
            "api_url": api_url,
            "has_api_key": has_api_key,
            "is_active": source.is_active,
            "last_scanned_at": source.last_scanned_at.isoformat() if source.last_scanned_at else None,
            "last_error_at": source.last_error_at.isoformat() if source.last_error_at else None,
            "has_recent_errors": has_recent_errors,
            "status": "error" if has_recent_errors else ("configured" if api_url and has_api_key else "incomplete"),
        })
    
    return {
        "total_active_sources": len(sources),
        "sources": result
    }
