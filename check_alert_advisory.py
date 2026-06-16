#!/usr/bin/env python3
"""Check advisory actions for a specific alert"""

import sys
from api.database import SessionLocal
from api.models import Alert, AdvisoryAction, InferenceResult, AdvisoryTemplate, Advisory

alert_id = "d3f24b2f-128d-480d-9499-5537098b8114"

db = SessionLocal()

print("=" * 80)
print(f"CHECKING ALERT: {alert_id}")
print("=" * 80)

alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()

if not alert:
    print(f"\n❌ Alert not found!")
    sys.exit(1)

print(f"\n✅ Alert found:")
print(f"   Hive ID: {alert.hive_id}")
print(f"   Severity: {alert.severity_level}")
print(f"   Status: {alert.action_status}")
print(f"   Recommended Action: {alert.recommended_action}")
print(f"   Inference ID: {alert.inference_id}")
print(f"   Timestamp: {alert.alert_timestamp}")

if not alert.inference_id:
    print(f"\n❌ No inference linked to this alert")
    sys.exit(0)

# Get inference
inference = db.query(InferenceResult).filter(
    InferenceResult.inference_id == alert.inference_id
).first()

if inference:
    print(f"\n📊 Inference Details:")
    print(f"   Hive State: {inference.hive_state}")
    print(f"   Confidence: {inference.confidence_score}")
    print(f"   Analyzed At: {inference.analyzed_at}")

# Get advisory actions
actions = db.query(AdvisoryAction).filter(
    AdvisoryAction.inference_id == alert.inference_id
).order_by(AdvisoryAction.priority_level, AdvisoryAction.created_at).all()

print(f"\n📋 Advisory Actions: {len(actions)}")

if not actions:
    print("   ❌ NO ADVISORY ACTIONS FOUND FOR THIS INFERENCE!")
    print("   This is why the mobile app shows no actions!")
else:
    for i, action in enumerate(actions, 1):
        print(f"\n   {i}. Action ID: {action.action_id}")
        print(f"      Priority: {action.priority_level}")
        print(f"      Title: {action.action_title}")
        print(f"      Description: {action.action_description}")
        print(f"      Status: {action.status}")
        print(f"      Template ID: {action.template_id}")
        print(f"      Advisory ID: {action.advisory_id}")
        
        # Get template info
        template = db.query(AdvisoryTemplate).filter(
            AdvisoryTemplate.template_id == action.template_id
        ).first()
        
        if template:
            print(f"      Template: {template.hive_state} ({template.advisory_type})")

print("\n" + "=" * 80)
db.close()
