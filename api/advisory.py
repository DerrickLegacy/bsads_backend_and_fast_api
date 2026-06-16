"""
Rule-based advisory generation.

When the model classifies a hive as a dangerous state, this module:
  1. Looks up the matching AdvisoryTemplate row (seeded in advisory_templates)
  2. Creates an Advisory copying the template's text/severity
  3. Creates AdvisoryAction checklist rows
  4. Creates an Alert linked to the Advisory

States that do NOT trigger alerts (no advisory needed):
  normal | queenbee_present | external_noise | uncertain
"""

from sqlalchemy.orm import Session

from api.models import (
    AdvisoryTemplate, Alert, Advisory, AdvisoryAction, Hive, InferenceResult
)

# Hardcoded fallback rules used when no matching advisory_template row exists.
# Keys match the unified hive_state vocabulary.
_FALLBACK_RULES: dict = {
    "swarm": {
        "severity_level":     "high",
        "recommended_action": "Immediate hive inspection required — swarm event detected",
        "advisory_type":      "Reactive",
        "condition_label":    "Swarm Detected",
        "advisory_text":      "A swarm event has been detected. Immediate action is required.",
        "severity":           "critical",
        "actions": [
            ("Inspect the hive immediately to confirm swarming activity",             "high"),
            ("Prepare a swarm trap or empty hive box nearby to capture the swarm",    "high"),
            ("Remove or destroy swarm cells to prevent secondary swarms",             "medium"),
            ("Ensure the hive has enough space to reduce overcrowding",               "medium"),
            ("Contact a local beekeeper association for immediate assistance",        "low"),
        ],
    },
    "pre_swarm": {
        "severity_level":     "medium",
        "recommended_action": "Pre-swarm indicators detected — inspect hive soon",
        "advisory_type":      "Preventive",
        "condition_label":    "Pre-Swarm Activity",
        "advisory_text":      "Pre-swarm activity detected. Early intervention can prevent a full swarm.",
        "severity":           "high",
        "actions": [
            ("Inspect for overcrowding and add supers if needed",                    "high"),
            ("Check for and remove swarm cells",                                      "medium"),
            ("Ensure adequate ventilation in the hive",                              "medium"),
            ("Schedule a full hive inspection within 48 hours",                      "low"),
        ],
    },
    "missing_queen": {
        "severity_level":     "medium",
        "recommended_action": "Queen absence detected — hive inspection needed",
        "advisory_type":      "Reactive",
        "condition_label":    "Queen Absence Suspected",
        "advisory_text":      "Signs of a queenless hive detected. Inspect and re-queen if necessary.",
        "severity":           "high",
        "actions": [
            ("Open the hive carefully and inspect all frames for the queen",          "high"),
            ("Look for fresh eggs (under 3 days old)",                               "high"),
            ("Check for emergency queen cells built by the colony",                  "medium"),
            ("Introduce a new mated queen if queen is confirmed absent for 3+ days", "medium"),
            ("Monitor the hive daily for the next 7 days to track recovery",         "low"),
        ],
    },
    "abscondment": {
        "severity_level":     "high",
        "recommended_action": "Hive abscondment detected — colony may have abandoned the hive",
        "advisory_type":      "Reactive",
        "condition_label":    "Abscondment Detected",
        "advisory_text":      "The colony may have absconded. Inspect the hive immediately.",
        "severity":           "critical",
        "actions": [
            ("Inspect the hive to confirm whether bees are still present",            "high"),
            ("Identify and address the root cause (pests, disease, heat stress)",     "high"),
            ("Clean and re-bait the hive to attract a new swarm",                    "medium"),
        ],
    },
    "pest_infested": {
        "severity_level":     "medium",
        "recommended_action": "Pest infestation indicators detected",
        "advisory_type":      "Reactive",
        "condition_label":    "Pest Infestation detected",
        "advisory_text":      "Pest activity detected in the hive. Treatment may be required.",
        "severity":           "high",
        "actions": [
            ("Inspect the hive for varroa mites, wax moths, or small hive beetles",  "high"),
            ("Apply appropriate treatment based on the identified pest",              "high"),
            ("Clean and remove debris from the hive floor",                           "medium"),
            ("Re-inspect after 7 days to confirm treatment effectiveness",            "low"),
        ],
    },
}

# States that never generate alerts/advisories
_SILENT_STATES = {"normal", "queenbee_present", "external_noise", "uncertain"}


def generate(
    inference: InferenceResult,
    hive: Hive,
    db: Session,
) -> None:
    """
    If the classified state warrants an alert, create Alert + Advisory +
    AdvisoryAction rows and commit them.  Safe to call for any state —
    silently does nothing for silent states.
    """
    if inference.hive_state in _SILENT_STATES:
        # Update hive current_state even for non-alerting states
        hive.current_state = inference.hive_state
        return

    # --- Try to look up advisory template from the database ---
    template = db.query(AdvisoryTemplate).filter(
        AdvisoryTemplate.hive_state == inference.hive_state
    ).first()

    rule = _FALLBACK_RULES.get(inference.hive_state)
    if template is None and rule is None:
        # Unknown state — just update hive state, no alert
        hive.current_state = inference.hive_state
        return

    # Populate advisory data preferring the database template
    advisory_type   = template.advisory_type   if template else rule["advisory_type"]
    condition_label = template.hive_state      if template else rule["condition_label"]
    advisory_text   = template.description     if template else rule["advisory_text"]
    severity        = template.severity        if template else rule["severity"]
    template_id     = template.template_id     if template else None

    severity_level     = rule["severity_level"]     if rule else severity
    recommended_action = rule["recommended_action"] if rule else advisory_text

    # --- Advisory (using template or creating new for this inference) ---
    # Create an advisory record for the inference
    advisory = Advisory(
        template_id        = template_id,
        action_title       = condition_label,
        action_description = advisory_text,
        priority_level     = severity_level,
        confidence_threshold_min = inference.confidence_score,
        confidence_threshold_max = 1.00,
        action_order       = 1,
        is_active          = True,
    )
    db.add(advisory)
    db.flush()  # get advisory.advisory_id before creating actions

    # --- Alert (linked to the hive and inference) ---
    alert = Alert(
        hive_id            = hive.hive_id,
        inference_id       = inference.inference_id,
        severity_level     = severity_level,
        recommended_action = recommended_action,
        action_status      = "pending",
    )
    db.add(alert)

    # --- Advisory Actions (checklist) from fallback rule ---
    # Create multiple actionable items for this specific inference
    if rule and rule.get("actions"):
        for idx, (description, priority) in enumerate(rule["actions"], start=1):
            db.add(AdvisoryAction(
                inference_id       = inference.inference_id,
                hive_id            = hive.hive_id,
                advisory_id        = advisory.advisory_id,
                template_id        = template_id,
                confidence_score   = inference.confidence_score,
                action_title       = f"{condition_label} - Action {idx}",
                action_description = description,
                priority_level     = priority,
                status             = "pending",
            ))

    # Update the hive's current known state
    hive.current_state = inference.hive_state
