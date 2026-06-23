"""
Queen Absence Watcher
=====================
Runs on a schedule (default: every 6 hours).

For every active hive that has received at least one inference:
  - If the last `queenbee_present` inference is MORE than 48 hours ago
    (or has never been seen at all), AND
  - No `missing_queen` alert was already raised in the last 48 hours,

→ Create an Alert + AdvisoryActions using the `queenbee_present` template
  so the farmer is notified to inspect for queen presence.

Why use the `queenbee_present` template for an ABSENCE alert?
  The template holds the "what to do when you haven't seen the queen"
  advisory library.  The alert title comes from the template description
  which is already set to:
  "No queen presence detected in the last 48 hours — colony may be queenless"
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models import (
    Advisory, AdvisoryAction, AdvisoryTemplate,
    Alert, Hive, InferenceResult,
)
from api.push_notifications import send_alert_notifications
import asyncio, threading

logger = logging.getLogger("bsads.queen_watcher")

ABSENCE_WINDOW_HOURS = 48    # Raise alert if queen not seen for this many hours
COOLDOWN_HOURS       = 48    # Don't raise another alert within this window


def _run_async(coro):
    def _target():
        asyncio.run(coro)
    threading.Thread(target=_target, daemon=True).start()


def check_queen_absence() -> None:
    """
    Scan all active hives.  For each hive that has gone more than
    ABSENCE_WINDOW_HOURS without a `queenbee_present` inference, raise
    a queen-absence alert (unless one was already raised recently).
    """
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        window_start = now - timedelta(hours=ABSENCE_WINDOW_HOURS)
        cooldown_start = now - timedelta(hours=COOLDOWN_HOURS)

        # Load the queenbee_present template (used for both the advisory
        # library lookup AND the alert metadata)
        template = db.query(AdvisoryTemplate).filter(
            AdvisoryTemplate.hive_state == "queenbee_present"
        ).first()
        if template is None:
            logger.warning("queen_watcher: no advisory_template for queenbee_present")
            return

        # Load all active advisory library actions for this template
        advisory_actions = db.query(Advisory).filter(
            Advisory.template_id == template.template_id,
            Advisory.is_active == True,
        ).order_by(Advisory.action_order).all()

        # All active hives that have had at least one inference
        hives = (
            db.query(Hive)
            .filter(Hive.is_deleted == False)
            .all()
        )

        alerts_raised = 0
        for hive in hives:
            hive_id = hive.hive_id

            # 1. Has the hive had ANY inference at all?
            total = (
                db.query(InferenceResult)
                .filter(InferenceResult.hive_id == hive_id)
                .count()
            )
            if total == 0:
                continue   # New hive, nothing to judge yet

            # 2. When was the last queenbee_present inference?
            last_queen = (
                db.query(InferenceResult.analyzed_at)
                .filter(
                    InferenceResult.hive_id == hive_id,
                    InferenceResult.hive_state == "queenbee_present",
                )
                .order_by(InferenceResult.analyzed_at.desc())
                .first()
            )

            last_queen_at = last_queen[0] if last_queen else None

            # Queen was seen within the window → no alert needed
            if last_queen_at is not None and last_queen_at >= window_start:
                continue

            # 3. Has a queen-absence alert already been raised in the cooldown window?
            recent_alert = (
                db.query(Alert)
                .filter(
                    Alert.hive_id == hive_id,
                    Alert.recommended_action.ilike("%queen%"),
                    Alert.alert_timestamp >= cooldown_start,
                )
                .first()
            )
            if recent_alert:
                continue   # Already alerted recently — don't spam

            # 4. Raise the alert
            hours_since = (
                round((now - last_queen_at).total_seconds() / 3600, 1)
                if last_queen_at else None
            )
            if hours_since:
                detail = f"No queen presence detected for {hours_since}h — colony may be queenless"
            else:
                detail = template.description or "No queen presence ever detected — inspect immediately"

            alert = Alert(
                hive_id=hive_id,
                inference_id=None,          # Not linked to a single inference
                severity_level=template.severity,
                recommended_action=detail,
                action_status="pending",
            )
            db.add(alert)
            db.flush()

            # 5. Copy advisory actions from the library
            for adv in advisory_actions:
                db.add(AdvisoryAction(
                    inference_id=None,
                    hive_id=hive_id,
                    advisory_id=adv.advisory_id,
                    template_id=template.template_id,
                    confidence_score=0.0,
                    action_title=adv.action_title,
                    action_description=adv.action_description,
                    priority_level=adv.priority_level,
                    status="pending",
                ))

            # 6. Push notification
            _run_async(send_alert_notifications(alert, db))

            alerts_raised += 1
            logger.info(
                f"queen_watcher: raised queen-absence alert for hive {hive.hive_name} "
                f"({hive_id}) — last seen {hours_since}h ago"
            )

        db.commit()
        if alerts_raised:
            logger.info(f"queen_watcher: raised {alerts_raised} queen-absence alert(s)")
        else:
            logger.info("queen_watcher: all hives have recent queen activity — no alerts needed")

    except Exception as exc:
        db.rollback()
        logger.exception(f"queen_watcher: error during check: {exc}")
    finally:
        db.close()
