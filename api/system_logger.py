"""
Thin wrapper that writes a SystemLog row to the database.

Usage (any module that already has a db session):
    from api.system_logger import log

    log(db, "info", "inference", "Hive classified as swarming",
        hive_id=hive.hive_id, audio_id=audio_id,
        details={"confidence": 0.98, "latency_ms": 2300})

Usage from background tasks / poller (no session passed in):
    from api.system_logger import log_standalone

    log_standalone("error", "poller", "HTTP API connection failed",
                   hive_id=source.hive_id,
                   details={"error": str(exc)})
"""

import traceback as _tb
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models import SystemLog


def log(
    db: Session,
    level: str,
    event_type: str,
    message: str,
    *,
    hive_id: str | None = None,
    user_id: str | None = None,
    audio_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Write a log row using an existing open session. Does NOT commit — caller handles that."""
    try:
        entry = SystemLog(
            level=level,
            event_type=event_type,
            message=message,
            details=details,
            hive_id=hive_id,
            user_id=user_id,
            audio_id=audio_id,
        )
        db.add(entry)
    except Exception:
        # Logging must never crash the caller
        pass


def log_standalone(
    level: str,
    event_type: str,
    message: str,
    *,
    hive_id: str | None = None,
    user_id: str | None = None,
    audio_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Open its own session, write, commit, and close. For use in background threads / pollers.
    Also prints to console for real-time monitoring.
    """
    # Print to console for real-time visibility
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    level_emoji = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "critical": "🔥"
    }.get(level, "•")
    
    console_msg = f"[{timestamp}] {level_emoji} [{event_type}] {message}"
    if hive_id:
        console_msg += f" (hive: {hive_id[:8]}...)"
    print(console_msg)
    
    # Write to database
    db: Session = SessionLocal()
    try:
        entry = SystemLog(
            level=level,
            event_type=event_type,
            message=message,
            details=details,
            hive_id=hive_id,
            user_id=user_id,
            audio_id=audio_id,
        )
        db.add(entry)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def exc_details(exc: Exception) -> dict[str, Any]:
    """Return a details dict with exception type and full traceback string."""
    return {
        "exception": type(exc).__name__,
        "traceback": _tb.format_exc(),
    }
