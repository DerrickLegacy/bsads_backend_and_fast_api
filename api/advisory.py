"""
Rule-based advisory generation.

When the model classifies a hive as 'swarming' or 'missing_queen',
this module creates an Alert and an Advisory with a checklist of
recommended actions stored in AdvisoryAction rows.

States that do NOT trigger alerts:
  active_colony | queenbee_present | external_noise
"""

from sqlalchemy.orm import Session

from api.models import Alert, Advisory, AdvisoryAction, Hive, InferenceResult

# ---------------------------------------------------------------------------
# Rules: hive_state → what alert and advisory actions to create
# ---------------------------------------------------------------------------
_RULES: dict = {
    "swarming": {
        "severity_level":     "High",
        "recommended_action": "Immediate hive inspection required — swarm event detected",
        "advisory_type":      "Reactive",
        "actions": [
            ("Inspect the hive immediately to confirm swarming activity",             "High"),
            ("Prepare a swarm trap or empty hive box nearby to capture the swarm",    "High"),
            ("Remove or destroy swarm cells to prevent secondary swarms",             "Medium"),
            ("Ensure the hive has enough space to reduce overcrowding",               "Medium"),
            ("Contact a local beekeeper association for immediate assistance",        "Low"),
        ],
    },
    "missing_queen": {
        "severity_level":     "Medium",
        "recommended_action": "Queen absence detected — hive inspection needed",
        "advisory_type":      "Reactive",
        "actions": [
            ("Open the hive carefully and inspect all frames for the queen",          "High"),
            ("Look for fresh eggs (under 3 days old) — their presence means the queen was recently active", "High"),
            ("Check for emergency queen cells built by the colony",                  "Medium"),
            ("Introduce a new mated queen if queen is confirmed absent for 3+ days", "Medium"),
            ("Monitor the hive daily for the next 7 days to track recovery",         "Low"),
        ],
    },
}


def generate(
    inference: InferenceResult,
    hive: Hive,
    db: Session,
) -> None:
    """
    If the classified state warrants an alert, create Alert + Advisory +
    AdvisoryAction rows and commit them.  Safe to call for any state —
    silently does nothing for normal states.
    """
    rule = _RULES.get(inference.hive_state)
    if rule is None:
        return  # normal state — no alert needed

    # --- Alert ---
    alert = Alert(
        hive_id            = hive.hive_id,
        inference_id       = inference.inference_id,
        severity_level     = rule["severity_level"],
        recommended_action = rule["recommended_action"],
        action_status      = "pending",
    )
    db.add(alert)

    # --- Advisory (container) ---
    advisory = Advisory(
        inference_id  = inference.inference_id,
        hive_id       = hive.hive_id,
        advisory_type = rule["advisory_type"],
    )
    db.add(advisory)
    db.flush()  # get advisory.advisory_id before creating actions

    # --- Advisory Actions (checklist) ---
    for description, priority in rule["actions"]:
        db.add(AdvisoryAction(
            advisory_id        = advisory.advisory_id,
            action_description = description,
            priority_level     = priority,
            status             = "pending",
        ))

    # Update the hive's current known state
    hive.current_state = inference.hive_state
