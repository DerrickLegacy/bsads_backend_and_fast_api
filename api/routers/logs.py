"""
System log endpoints — admin only.

GET /logs                  — paginated log feed with optional filters
GET /logs/{log_id}         — single log entry
DELETE /logs               — purge old logs (admin maintenance)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import SystemLog, User
from api.routers.auth import get_current_user
from api.schemas import SystemLogResponse

router = APIRouter(prefix="/logs", tags=["System Logs"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.get("", response_model=list[SystemLogResponse])
def list_logs(
    level:      Optional[str] = Query(None, description="Filter by level: info | warning | error | critical"),
    event_type: Optional[str] = Query(None, description="Filter by event_type: inference | poller | http_api | auth | upload | advisory | system"),
    hive_id:    Optional[str] = Query(None, description="Filter logs for a specific hive"),
    since:      Optional[datetime] = Query(None, description="Only logs created after this ISO datetime"),
    limit:      int = Query(100, ge=1, le=1000, description="Maximum rows to return"),
    offset:     int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """
    Return system log entries, newest first.
    Combine any filters: ?level=error&event_type=http_api&limit=50
    """
    q = db.query(SystemLog)

    if level:
        q = q.filter(SystemLog.level == level)
    if event_type:
        q = q.filter(SystemLog.event_type == event_type)
    if hive_id:
        q = q.filter(SystemLog.hive_id == hive_id)
    if since:
        q = q.filter(SystemLog.created_at >= since)

    return (
        q.order_by(SystemLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/summary")
def log_summary(
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """
    Count of log entries grouped by level — useful for a dashboard health widget.
    """
    from sqlalchemy import func
    rows = (
        db.query(SystemLog.level, func.count(SystemLog.log_id).label("count"))
        .group_by(SystemLog.level)
        .all()
    )
    return {row.level: row.count for row in rows}


@router.get("/{log_id}", response_model=SystemLogResponse)
def get_log(
    log_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """Return a single log entry by ID."""
    entry = db.query(SystemLog).filter(SystemLog.log_id == log_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return entry


@router.delete("", status_code=status.HTTP_200_OK)
def purge_logs(
    older_than: datetime = Query(..., description="Delete all logs created before this ISO datetime"),
    level:      Optional[str] = Query(None, description="Only delete logs of this level"),
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """
    Delete log entries older than a given datetime.
    Optionally restrict to a single level (e.g. purge only 'info' noise).

    Example: DELETE /logs?older_than=2026-01-01T00:00:00&level=info
    """
    q = db.query(SystemLog).filter(SystemLog.created_at < older_than)
    if level:
        q = q.filter(SystemLog.level == level)

    deleted = q.count()
    q.delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted, "older_than": older_than.isoformat()}
