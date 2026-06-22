"""
Rule-based advisory generation with confidence threshold-based action selection.

When the model classifies a hive in a concerning state, this module:
  1. Looks up the AdvisoryTemplate for the classification
  2. Queries advisories table for actions matching the confidence score
  3. Creates AdvisoryAction records for the specific inference
  4. Creates an Alert linked to the inference
  5. Sends push notifications via Expo Push API

States that do NOT trigger alerts (no advisory needed):
  normal | queenbee_present | external_noise | uncertain
"""

import asyncio
import threading
from sqlalchemy.orm import Session
from typing import List

from api.models import (
    AdvisoryTemplate, Alert, Advisory, AdvisoryAction, Hive, InferenceResult
)
from api.push_notifications import send_alert_notifications

# States that never generate alerts/advisories
_SILENT_STATES = {"normal", "queenbee_present", "external_noise", "uncertain"}


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
    If the classified state warrants an alert, create Alert + AdvisoryAction
    rows based on confidence threshold matching and commit them.
    
    Safe to call for any state — silently does nothing for non-alerting states.
    """
    hive_state = inference.hive_state
    confidence = float(inference.confidence_score)
    
    # Update hive current_state regardless
    hive.current_state = hive_state
    
    if hive_state in _SILENT_STATES:
        return

    # --- Look up advisory template from database ---
    template = db.query(AdvisoryTemplate).filter(
        AdvisoryTemplate.hive_state == hive_state
    ).first()

    if template is None:
        # Unknown state — just update hive state, no alert
        return

    # Check if confidence meets minimum threshold
    if confidence < float(template.min_confidence_threshold):
        # Confidence too low to trigger actions
        return

    # --- Query advisories that match this classification and confidence ---
    matching_actions = db.query(Advisory).filter(
        Advisory.template_id == template.template_id,
        Advisory.is_active == True,
        Advisory.confidence_threshold_min <= confidence,
        Advisory.confidence_threshold_max >= confidence
    ).order_by(Advisory.action_order).all()

    if not matching_actions:
        # No matching actions for this confidence level
        return

    # --- Create Alert ---
    # Use admin-configured template description as the summary — no hardcoded text
    recommended_action = (
        template.description
        or f"{len(matching_actions)} action(s) recommended for {hive_state.replace('_', ' ')}"
    )

    alert = Alert(
        hive_id=hive.hive_id,
        inference_id=inference.inference_id,
        severity_level=template.severity,
        recommended_action=recommended_action,
        action_status="pending",
    )
    db.add(alert)
    db.flush()

    # --- Create AdvisoryAction records for this specific inference ---
    for action_template in matching_actions:
        advisory_action = AdvisoryAction(
            inference_id=inference.inference_id,
            hive_id=hive.hive_id,
            advisory_id=action_template.advisory_id,
            template_id=template.template_id,
            confidence_score=confidence,
            action_title=action_template.action_title,
            action_description=action_template.action_description,
            priority_level=action_template.priority_level,
            status="pending",
        )
        db.add(advisory_action)

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
