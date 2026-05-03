from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Alert, Hive, User
from api.routers.auth import get_current_user
from api.schemas import AlertResponse

router = APIRouter(prefix="/hives", tags=["Alerts"])


@router.get("/{hive_id}/alerts", response_model=list[AlertResponse])
def get_alerts(
    hive_id: int,
    only_pending: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return alerts for a hive.
    By default only returns unacknowledged (pending) alerts.
    Pass ?only_pending=false to see all alerts including acknowledged ones.
    """
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.user_id == current_user.user_id,
    ).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    query = db.query(Alert).filter(Alert.hive_id == hive_id)
    if only_pending:
        query = query.filter(Alert.action_status == "pending")

    return query.order_by(Alert.generated_at.desc()).all()


@router.patch("/{hive_id}/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    hive_id: int,
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an alert as acknowledged — farmer has seen and acted on it."""
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.user_id == current_user.user_id,
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
