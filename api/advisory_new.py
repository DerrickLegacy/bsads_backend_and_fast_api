"""
Rule-based advisory generation with confidence threshold-based action selection.

When the model classifies a hive in a concerning state, this module:
  1. Looks up the AdvisoryTemplate for the classification
  2. Always creates an Alert for any non-silent dangerous state
  3. Attaches AdvisoryAction records from the advisory library when available
  4. Sends push notifications via Expo Push API

States that do NOT trigger alerts (no advisory needed):
  normal | queenbee_present | external_noise | uncertain

Design guarantee:
  An Alert is ALWAYS created for alerting states regardless of whether the
  advisory library has matching rows.  Advisory actions are a bonus — they
  enrich the alert with a checklist but their absence never blocks the alert.
"""

import asyncio
import threading
from sqlalchemy.orm import Session
from typing import List

from api.models import (
    AdvisoryTemplate, Alert, Advisory, AdvisoryAction, Hive, InferenceResult
)
from api.push_notifications import send_alert_notifications

# No states are permanently silent — every classification gets an alert.
# The advisory library (advisories table) controls what actions are shown.
# States with no advisory rows will still get an alert with the template description.
_SILENT_STATES: set = set()


def _run_async_in_thread(coro, db):
    """Run an async coroutine in a separate thread to avoid blocking."""
    def thread_target():
        asyncio.run(coro)
    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()


def generate(
    inference: InferenceResult,
    hive: Hive,
    db: Session,
) -> None:
    """
    Create an Alert + AdvisoryAction rows for any dangerous hive state.

    The Alert is always created when the state is not silent — advisory
    library rows are attached when they exist but their absence never
    prevents the alert from being raised.

    Safe to call for any state — silently does nothing for non-alerting states.
    """
    hive_state = inference.hive_state
    confidence = float(inference.confidence_score)

    # Update hive current_state only if hive is not None
    # (processing.py also updates this — guard here defensively)
    if hive is not None:
        hive.current_state = hive_state

    if hive_state in _SILENT_STATES:
        return

    # --- Look up advisory template ---
    template = db.query(AdvisoryTemplate).filter(
        AdvisoryTemplate.hive_state == hive_state
    ).first()

    if template is None:
        # Completely unknown state — still update hive state, but no alert
        return

    # --- Always create the Alert for any alerting state ---
    recommended_action = (
        template.description
        or f"{hive_state.replace('_', ' ').title()} detected — inspect your hive"
    )

    alert = Alert(
        hive_id=inference.hive_id,
        inference_id=inference.inference_id,
        severity_level=template.severity,
        recommended_action=recommended_action,
        action_status="pending",
    )
    db.add(alert)
    db.flush()  # Populate alert.alert_id before using it below

    # --- Attach matching AdvisoryAction rows (best-effort) ---
    matching_actions = db.query(Advisory).filter(
        Advisory.template_id == template.template_id,
        Advisory.is_active == True,
        Advisory.confidence_threshold_min <= confidence,
        Advisory.confidence_threshold_max >= confidence,
    ).order_by(Advisory.action_order).all()

    # Fallback: if nothing matched the exact confidence band, grab all active
    # actions for this template so the alert always has a checklist.
    if not matching_actions:
        matching_actions = db.query(Advisory).filter(
            Advisory.template_id == template.template_id,
            Advisory.is_active == True,
        ).order_by(Advisory.action_order).all()

    for action_template in matching_actions:
        advisory_action = AdvisoryAction(
            inference_id=inference.inference_id,
            hive_id=inference.hive_id,
            advisory_id=action_template.advisory_id,
            template_id=template.template_id,
            confidence_score=confidence,
            action_title=action_template.action_title,
            action_description=action_template.action_description,
            priority_level=action_template.priority_level,
            status="pending",
        )
        db.add(advisory_action)

    # Flush so all advisory_actions get IDs — caller commits the transaction
    db.flush()

    # --- Send push notifications ---
    _run_async_in_thread(send_alert_notifications(alert, db), db)


def get_actions_for_inference(
    inference_id: str,
    db: Session
) -> List[AdvisoryAction]:
    """
    Retrieve all suggested actions for a specific inference.
    Used by API endpoints to show farmers what actions to take.
    """
    return db.query(AdvisoryAction).filter(
        AdvisoryAction.inference_id == inference_id
    ).order_by(
        AdvisoryAction.priority_level.desc(),
        AdvisoryAction.created_at
    ).all()


def get_actions_for_hive(
    hive_id: str,
    db: Session,
    status: str = None
) -> List[AdvisoryAction]:
    """
    Retrieve all actions for a hive, optionally filtered by status.
    Useful for showing pending actions across all recent inferences.
    """
    query = db.query(AdvisoryAction).filter(
        AdvisoryAction.hive_id == hive_id
    )
    
    if status:
        query = query.filter(AdvisoryAction.status == status)
    
    return query.order_by(
        AdvisoryAction.created_at.desc()
    ).all()


def update_action_status(
    action_id: str,
    status: str,
    notes: str,
    db: Session
) -> AdvisoryAction:
    """
    Update the status of a specific action.
    Used when farmers mark actions as completed, in_progress, or skipped.
    """
    from datetime import datetime
    
    action = db.query(AdvisoryAction).filter(
        AdvisoryAction.action_id == action_id
    ).first()
    
    if action:
        action.status = status
        action.notes = notes
        if status == "completed":
            action.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(action)
    
    return action
