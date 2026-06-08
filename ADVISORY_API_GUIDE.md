# Advisory System API Guide

## Overview

The advisory system now has **automatic** advisory action generation based on ML inference results. When audio is processed and an inference is created, advisory actions are **automatically** generated if the confidence threshold is met.

---

## System Flow

### Automatic Advisory Generation

```
1. Audio uploaded/discovered
   ↓
2. Inference engine processes audio
   ↓
3. InferenceResult created with confidence score
   ↓
4. advisory_new.generate() AUTOMATICALLY called
   ↓
5. System looks up AdvisoryTemplate by hive_state
   ↓
6. If confidence >= min_confidence_threshold:
   - Queries advisories (action library) for matching actions
   - Creates AdvisoryAction records for this inference
   - Creates Alert record
   ↓
7. Farmer sees suggested actions in app
```

**Key Point:** Advisory actions are **automatically created** when inference results are generated. No manual triggering needed!

---

## API Endpoints

### 1. Advisory Templates (Classification Definitions)

Managed by admins to define hive states and their thresholds.

#### **GET /advisory-templates**
List all classification templates.

**Response:**
```json
[
  {
    "template_id": 3,
    "prediction_code": 2.0,
    "hive_state": "swarm",
    "advisory_type": "Reactive",
    "severity": "critical",
    "min_confidence_threshold": 0.8000,
    "description": "Active swarm event detected"
  }
]
```

#### **POST /advisory-templates** (Admin only)
Create a new classification.

**Request:**
```json
{
  "prediction_code": 9.0,
  "hive_state": "disease_detected",
  "advisory_type": "Reactive",
  "severity": "high",
  "min_confidence_threshold": 0.75,
  "description": "Disease indicators detected in hive"
}
```

#### **PUT /advisory-templates/{template_id}** (Admin only)
Update a classification.

**Request:**
```json
{
  "min_confidence_threshold": 0.85,
  "description": "Updated description"
}
```

#### **DELETE /advisory-templates/{template_id}** (Admin only)
Delete a classification.

---

### 2. Advisory Library (Reusable Action Definitions)

Managed by admins to define all possible actions for each classification.

#### **GET /advisory-library**
List all actions in the library.

**Query Parameters:**
- `template_id` (optional): Filter by classification
- `is_active` (optional): Filter by active status

**Response:**
```json
[
  {
    "advisory_id": "a006",
    "template_id": 3,
    "action_title": "Immediate Hive Inspection",
    "action_description": "Inspect the hive immediately to confirm swarming activity.",
    "priority_level": "high",
    "confidence_threshold_min": 0.8000,
    "confidence_threshold_max": 1.0000,
    "action_order": 1,
    "is_active": true
  }
]
```

#### **GET /advisory-library/by-classification/{hive_state}**
Get all actions for a specific classification.

**Example:** `GET /advisory-library/by-classification/swarm`

**Response:** Same as above, filtered by hive_state.

#### **POST /advisory-library** (Admin only)
Add a new action to the library.

**Request:**
```json
{
  "template_id": 3,
  "action_title": "Contact Local Swarm Hotline",
  "action_description": "Call the local beekeeping swarm hotline at 555-SWARM for immediate assistance.",
  "priority_level": "high",
  "confidence_threshold_min": 0.90,
  "confidence_threshold_max": 1.00,
  "action_order": 10,
  "is_active": true
}
```

#### **PUT /advisory-library/{advisory_id}** (Admin only)
Update an action in the library.

**Request:**
```json
{
  "action_description": "Updated description with more details",
  "confidence_threshold_min": 0.85
}
```

#### **DELETE /advisory-library/{advisory_id}** (Admin only)
Remove an action from the library.

#### **PATCH /advisory-library/{advisory_id}/toggle** (Admin only)
Toggle active status (deactivate without deleting).

---

### 3. Advisory Actions (Inference-Specific Suggestions)

**These are AUTOMATICALLY created** when inference results are generated.

#### **GET /advisory-actions/inference/{inference_id}**
Get all suggested actions for a specific inference.

**Response:**
```json
[
  {
    "action_id": "act-001",
    "inference_id": "inf-2024-001",
    "hive_id": "hive-05",
    "template_id": 3,
    "hive_state": "swarm",
    "confidence_score": 0.8500,
    "action_title": "Immediate Hive Inspection",
    "action_description": "Inspect the hive immediately to confirm swarming activity.",
    "priority_level": "high",
    "status": "pending",
    "completed_at": null,
    "notes": null,
    "created_at": "2026-06-08T09:15:23Z"
  }
]
```

#### **GET /advisory-actions/hive/{hive_id}**
Get all actions for a hive (across all inferences).

**Query Parameters:**
- `status_filter` (optional): Filter by status (pending, in_progress, completed, skipped)
- `limit` (optional, default 50): Max number of actions to return

**Example:** `GET /advisory-actions/hive/hive-05?status_filter=pending&limit=20`

#### **GET /advisory-actions/hive/{hive_id}/pending-count**
Get count of pending actions for a hive.

**Response:**
```json
{
  "hive_id": "hive-05",
  "pending_count": 3
}
```

#### **GET /advisory-actions/user/pending**
Get all pending actions across all user's hives.

**Query Parameters:**
- `limit` (optional, default 100)

**Response:** Array of actions (same format as above)

#### **PATCH /advisory-actions/{action_id}/status**
Update action status (used by farmers).

**Request:**
```json
{
  "status": "completed",
  "notes": "Added 2 supers, bees have more space now"
}
```

**Valid statuses:**
- `pending` - Not started yet
- `in_progress` - Currently working on it
- `completed` - Finished
- `skipped` - Decided not to do this

**Response:** Updated action object

---

## Usage Examples

### Example 1: Admin Sets Up New Classification

**Step 1:** Create classification template
```bash
POST /advisory-templates
{
  "prediction_code": 10.0,
  "hive_state": "robbing",
  "advisory_type": "Reactive",
  "severity": "high",
  "min_confidence_threshold": 0.70,
  "description": "Other bees robbing this hive"
}
```

**Step 2:** Add actions to library
```bash
POST /advisory-library
{
  "template_id": 10,
  "action_title": "Reduce Entrance Size",
  "action_description": "Immediately reduce the hive entrance to help bees defend.",
  "priority_level": "high",
  "confidence_threshold_min": 0.70,
  "confidence_threshold_max": 1.00,
  "action_order": 1
}

POST /advisory-library
{
  "template_id": 10,
  "action_title": "Install Robber Screen",
  "action_description": "Install a robber screen to confuse robbing bees.",
  "priority_level": "high",
  "confidence_threshold_min": 0.80,
  "confidence_threshold_max": 1.00,
  "action_order": 2
}
```

**Step 3:** Actions are now automatically suggested when ML detects robbing!

---

### Example 2: Farmer Workflow

**Audio gets processed → Inference created → Actions AUTOMATICALLY generated**

**Step 1:** Farmer views alert
```bash
GET /alerts/hive/hive-05
```

**Step 2:** Farmer views suggested actions
```bash
GET /advisory-actions/inference/inf-2024-001
```

**Step 3:** Farmer starts working on first action
```bash
PATCH /advisory-actions/act-001/status
{
  "status": "in_progress",
  "notes": "Started inspection at 2pm"
}
```

**Step 4:** Farmer completes action
```bash
PATCH /advisory-actions/act-001/status
{
  "status": "completed",
  "notes": "Confirmed swarming. Found swarm on nearby tree branch."
}
```

**Step 5:** Farmer checks pending tasks
```bash
GET /advisory-actions/hive/hive-05?status_filter=pending
```

---

### Example 3: Mobile App Dashboard

**Get all pending tasks for logged-in farmer:**
```bash
GET /advisory-actions/user/pending?limit=50
```

**Response shows:**
- All pending actions across all hives
- Sorted by priority (high first)
- Can be displayed as a to-do list

**Get pending count badge for each hive:**
```bash
GET /advisory-actions/hive/hive-05/pending-count
GET /advisory-actions/hive/hive-12/pending-count
GET /advisory-actions/hive/hive-18/pending-count
```

**Response:**
```json
{ "hive_id": "hive-05", "pending_count": 3 }
{ "hive_id": "hive-12", "pending_count": 0 }
{ "hive_id": "hive-18", "pending_count": 5 }
```

Display badges on hive cards in mobile app!

---

## How Confidence Thresholds Work

### Template-Level Threshold
```json
{
  "template_id": 3,
  "hive_state": "swarm",
  "min_confidence_threshold": 0.80
}
```
- **If inference confidence < 0.80:** No actions generated at all
- **If inference confidence >= 0.80:** Actions are generated

### Action-Level Thresholds
```json
{
  "advisory_id": "a018",
  "action_title": "EMERGENCY: Swarm in Progress",
  "confidence_threshold_min": 0.90,
  "confidence_threshold_max": 1.00
}
```
- This action ONLY suggested if confidence is between 0.90 and 1.00
- Allows emergency actions for high confidence cases

### Combined Example

**Swarm template:** min_confidence = 0.80

**Actions:**
- Action A: 0.80 - 1.00 (always shown if swarm detected)
- Action B: 0.90 - 1.00 (only shown for high confidence)
- Action C: 0.95 - 1.00 (only shown for very high confidence)

**Result:**
- Inference at 79%: No actions (below template threshold)
- Inference at 85%: Action A only
- Inference at 92%: Actions A + B
- Inference at 96%: Actions A + B + C

---

## Integration Points

### When Audio is Processed
```python
# In api/processing.py (ALREADY IMPLEMENTED)
inference = InferenceResult(...)
db.add(inference)
db.flush()

# AUTOMATICALLY generates advisory actions
advisory_module.generate(inference, hive, db)
```

### Mobile App Integration

**Hive Detail Screen:**
```javascript
// Get latest inference actions
GET /advisory-actions/hive/{hiveId}?limit=10

// Display as checklist with checkboxes
```

**To-Do List Screen:**
```javascript
// Get all pending tasks
GET /advisory-actions/user/pending

// Group by hive
// Show priority badges
```

**Action Item:**
```javascript
// When farmer taps checkbox
PATCH /advisory-actions/{actionId}/status
{
  "status": "completed",
  "notes": "Done at 3pm"
}
```

---

## Admin Panel Integration

### Template Management
```
Admin Dashboard
  └── Advisory Templates
      ├── List all classifications
      ├── Create new classification
      ├── Edit thresholds
      └── View associated actions
```

### Action Library Management
```
Admin Dashboard
  └── Action Library
      ├── List all actions
      ├── Filter by classification
      ├── Create new action
      ├── Edit thresholds and descriptions
      ├── Toggle active/inactive
      └── Delete unused actions
```

---

## Database Queries for Reports

### Most Completed Actions
```sql
SELECT 
  action_title,
  COUNT(*) as times_completed
FROM advisory_actions
WHERE status = 'completed'
GROUP BY action_title
ORDER BY times_completed DESC
LIMIT 10;
```

### Most Skipped Actions
```sql
SELECT 
  action_title,
  COUNT(*) as times_skipped
FROM advisory_actions
WHERE status = 'skipped'
GROUP BY action_title
ORDER BY times_skipped DESC
LIMIT 10;
```

### Action Completion Rate by Hive
```sql
SELECT 
  hive_id,
  COUNT(*) FILTER (WHERE status = 'completed') as completed,
  COUNT(*) FILTER (WHERE status = 'skipped') as skipped,
  COUNT(*) FILTER (WHERE status = 'pending') as pending,
  COUNT(*) as total
FROM advisory_actions
GROUP BY hive_id;
```

### Average Time to Complete Actions
```sql
SELECT 
  action_title,
  AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/3600) as avg_hours_to_complete
FROM advisory_actions
WHERE status = 'completed'
  AND completed_at IS NOT NULL
GROUP BY action_title
ORDER BY avg_hours_to_complete;
```

---

## Summary

✅ **Automatic Generation:** Advisory actions are created automatically when inference results are saved

✅ **Admin Management:** Admins manage classifications and action library via API

✅ **Farmer Interaction:** Farmers view and update action status via API

✅ **Confidence-Based:** Actions are selected based on ML confidence scores

✅ **Flexible:** Easy to add new classifications and actions without code changes

✅ **Trackable:** Full history of which actions were suggested and completed
