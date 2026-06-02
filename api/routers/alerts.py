from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

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


def _to_mobile(alert: Alert, index: int = 0) -> MobileAlertResponse:
    title = (
        alert.advisory.condition_label
        if alert.advisory and alert.advisory.condition_label
        else (alert.recommended_action or "Alert")
    )
    return MobileAlertResponse(
        id=alert.alert_id,
        hive_id=alert.hive_id,
        severity=alert.severity_level,
        title=title,
        date=alert.alert_timestamp.isoformat() if alert.alert_timestamp else "",
        summary=alert.recommended_action or "",
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
    q = db.query(Alert).options(joinedload(Alert.advisory))

    if current_user.role == "admin":
        if hive_id:
            q = q.filter(Alert.hive_id == hive_id)
    else:
        hive_ids = [
            row.hive_id
            for row in db.query(Hive.hive_id).filter(Hive.owner_id == current_user.user_id).all()
        ]
        if not hive_ids:
            return []
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

    alert = db.query(Alert).options(joinedload(Alert.advisory)).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.action_status = "sent"
    db.commit()
    db.refresh(alert)

    title = (alert.advisory.condition_label if alert.advisory and alert.advisory.condition_label
             else (alert.recommended_action or "Alert"))
    details = (alert.advisory.advisory_text if alert.advisory and alert.advisory.advisory_text
               else (alert.recommended_action or ""))

    return MobileAlertDetailResponse(
        id=alert.alert_id,
        hive_id=alert.hive_id,
        severity=alert.severity_level,
        title=title,
        time=alert.alert_timestamp.isoformat() if alert.alert_timestamp else "",
        details=details,
        acknowledged=alert.action_status == "acknowledged",
    )


@mobile_alerts_router.get("/{alert_id}", response_model=MobileAlertDetailResponse)
def get_alert_detail(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the detail of a single alert (mobile alert detail screen)."""
    hive_ids = [
        row.hive_id
        for row in db.query(Hive.hive_id).filter(Hive.owner_id == current_user.user_id).all()
    ]

    alert = (
        db.query(Alert)
        .options(joinedload(Alert.advisory))
        .filter(Alert.alert_id == alert_id, Alert.hive_id.in_(hive_ids))
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    title = (
        alert.advisory.condition_label
        if alert.advisory and alert.advisory.condition_label
        else (alert.recommended_action or "Alert")
    )
    details = (
        alert.advisory.advisory_text
        if alert.advisory and alert.advisory.advisory_text
        else (alert.recommended_action or "No details available.")
    )

    return MobileAlertDetailResponse(
        id=alert.alert_id,
        hive_id=alert.hive_id,
        severity=alert.severity_level,
        title=title,
        time=alert.alert_timestamp.isoformat() if alert.alert_timestamp else "",
        details=details,
        acknowledged=alert.action_status == "acknowledged",
    )


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
        alert = (
            db.query(Alert)
            .options(joinedload(Alert.advisory).joinedload(Advisory.actions))
            .filter(Alert.alert_id == alert_id)
            .first()
        )
    else:
        hive_ids = [
            row.hive_id
            for row in db.query(Hive.hive_id).filter(Hive.owner_id == current_user.user_id).all()
        ]
        alert = (
            db.query(Alert)
            .options(joinedload(Alert.advisory).joinedload(Advisory.actions))
            .filter(Alert.alert_id == alert_id, Alert.hive_id.in_(hive_ids))
            .first()
        )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if not alert.advisory:
        raise HTTPException(status_code=404, detail="No advisory linked to this alert")

    return alert.advisory


@mobile_alerts_router.post("/{alert_id}/acknowledge", response_model=MobileAlertDetailResponse)
def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an alert from the mobile app."""
    hive_ids = [
        row.hive_id
        for row in db.query(Hive.hive_id).filter(Hive.owner_id == current_user.user_id).all()
    ]

    alert = (
        db.query(Alert)
        .options(joinedload(Alert.advisory))
        .filter(Alert.alert_id == alert_id, Alert.hive_id.in_(hive_ids))
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.action_status = "acknowledged"
    db.commit()
    db.refresh(alert)

    title = (
        alert.advisory.condition_label
        if alert.advisory and alert.advisory.condition_label
        else (alert.recommended_action or "Alert")
    )
    details = (
        alert.advisory.advisory_text
        if alert.advisory and alert.advisory.advisory_text
        else (alert.recommended_action or "")
    )

    return MobileAlertDetailResponse(
        id=alert.alert_id,
        hive_id=alert.hive_id,
        severity=alert.severity_level,
        title=title,
        time=alert.alert_timestamp.isoformat() if alert.alert_timestamp else "",
        details=details,
        acknowledged=True,
    )
