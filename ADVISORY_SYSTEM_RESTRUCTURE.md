# Advisory System Restructure

## Overview

The advisory system has been restructured to separate:
1. **Classifications** (advisory_templates) 
2. **Action Library** (advisories)
3. **Inference-Specific Actions** (advisory_actions)

This allows dynamic action selection based on ML confidence scores.

---

## Table Structure

### 1. `advisory_templates` - Classification Definitions

**Purpose:** Defines each hive state classification with its properties

| Column | Type | Description |
|--------|------|-------------|
| template_id | BIGINT | Primary key |
| prediction_code | NUMERIC | ML model prediction code |
| hive_state | VARCHAR(50) | Classification name (swarm, pre_swarm, etc.) |
| advisory_type | VARCHAR(30) | Preventive or Reactive |
| severity | VARCHAR(20) | info, high, critical |
| min_confidence_threshold | NUMERIC(5,4) | Minimum confidence to trigger actions |
| description | TEXT | Description of this classification |

**Example Data:**

| template_id | prediction_code | hive_state | advisory_type | severity | min_confidence_threshold | description |
|-------------|----------------|------------|---------------|----------|-------------------------|-------------|
| 2 | 1.0 | pre_swarm | Preventive | high | 0.7000 | Pre-swarm indicators detected |
| 3 | 2.0 | swarm | Reactive | critical | 0.8000 | Active swarm event detected |
| 4 | 3.0 | missing_queen | Reactive | high | 0.7500 | Queen absence suspected |

---

### 2. `advisories` - Reusable Action Library

**Purpose:** All possible actions for each classification, with confidence thresholds

| Column | Type | Description |
|--------|------|-------------|
| advisory_id | UUID | Primary key |
| template_id | BIGINT | References advisory_templates |
| action_title | VARCHAR(200) | Short action title |
| action_description | TEXT | Detailed action steps |
| priority_level | VARCHAR(20) | high, medium, low |
| confidence_threshold_min | NUMERIC(5,4) | Min confidence to suggest this action |
| confidence_threshold_max | NUMERIC(5,4) | Max confidence for this action |
| action_order | INTEGER | Display order |
| is_active | BOOLEAN | Whether action is currently used |

**Example Data:**

| advisory_id | template_id | action_title | action_description | priority_level | confidence_threshold_min | confidence_threshold_max | action_order |
|-------------|-------------|--------------|-------------------|----------------|------------------------|------------------------|-------------|
| a001 | 2 | Inspect for Overcrowding | Check if hive is overcrowded and add supers if needed | high | 0.7000 | 1.0000 | 1 |
| a002 | 2 | Check and Remove Swarm Cells | Inspect all frames for swarm cells and remove them | high | 0.7500 | 1.0000 | 2 |
| a003 | 2 | Ensure Adequate Ventilation | Verify proper ventilation to prevent swarming | medium | 0.7000 | 1.0000 | 3 |
| a006 | 3 | Immediate Hive Inspection | Inspect hive immediately to confirm swarming activity | high | 0.8000 | 1.0000 | 1 |
| a007 | 3 | Prepare Swarm Trap | Set up swarm trap nearby to capture the swarm | high | 0.8000 | 1.0000 | 2 |
| a018 | 3 | EMERGENCY: Swarm in Progress | Drop everything and respond immediately | high | 0.9000 | 1.0000 | 1 |
| a019 | 3 | Call Emergency Backup | Contact experienced beekeepers immediately | high | 0.9000 | 1.0000 | 2 |

---

### 3. `advisory_actions` - Inference-Specific Suggested Actions

**Purpose:** Actual actions suggested for each hive inference based on confidence

| Column | Type | Description |
|--------|------|-------------|
| action_id | UUID | Primary key |
| inference_id | UUID | Which ML inference triggered this |
| hive_id | UUID | Which hive this is for |
| advisory_id | UUID | References the action template |
| template_id | BIGINT | References the classification |
| confidence_score | NUMERIC(5,4) | ML confidence score |
| action_title | VARCHAR(200) | Copied from advisory |
| action_description | TEXT | Copied from advisory |
| priority_level | VARCHAR(20) | Copied from advisory |
| status | VARCHAR(20) | pending, in_progress, completed, skipped |
| completed_at | TIMESTAMP | When farmer completed this |
| notes | TEXT | Farmer notes |

---

## Example Scenario: Swarm Detection

### Scenario 1: Low Confidence Swarm (85%)

**Inference:**
- `inference_id`: inf-2024-001
- `hive_id`: hive-05
- `hive_state`: swarm
- `confidence_score`: 0.8500

**What Happens:**
1. System looks up `advisory_templates` → finds template_id = 3 (swarm)
2. Checks threshold: 0.85 >= 0.80 (min_confidence_threshold) ✓
3. Queries `advisories` for actions where:
   - `template_id = 3`
   - `confidence_threshold_min <= 0.85`
   - `confidence_threshold_max >= 0.85`
4. Finds matching actions: a006, a007, a008, a009, a010, a011
5. Creates records in `advisory_actions`:

**Resulting `advisory_actions` records:**

| action_id | inference_id | hive_id | advisory_id | template_id | confidence_score | action_title | priority_level | status |
|-----------|--------------|---------|-------------|-------------|-----------------|--------------|----------------|--------|
| act-001 | inf-2024-001 | hive-05 | a006 | 3 | 0.8500 | Immediate Hive Inspection | high | pending |
| act-002 | inf-2024-001 | hive-05 | a007 | 3 | 0.8500 | Prepare Swarm Trap | high | pending |
| act-003 | inf-2024-001 | hive-05 | a008 | 3 | 0.8500 | Remove Secondary Swarm Cells | high | pending |
| act-004 | inf-2024-001 | hive-05 | a009 | 3 | 0.8500 | Add Space to Hive | medium | pending |
| act-005 | inf-2024-001 | hive-05 | a011 | 3 | 0.8500 | Document Swarm Event | low | pending |

**Note:** Action a010 (Contact Association) is NOT included because its confidence range is 0.80-0.90, but we want to exclude it at exactly 0.85. Action a018 and a019 are NOT included because they require 0.90+ confidence.

---

### Scenario 2: High Confidence Swarm (92%)

**Inference:**
- `inference_id`: inf-2024-002
- `hive_id`: hive-05
- `hive_state`: swarm
- `confidence_score`: 0.9200

**What Happens:**
1. Same template lookup (template_id = 3)
2. Queries `advisories` with confidence 0.92
3. Finds ADDITIONAL high-confidence actions: a018, a019
4. Creates more urgent action set:

**Resulting `advisory_actions` records:**

| action_id | inference_id | hive_id | advisory_id | template_id | confidence_score | action_title | priority_level | status |
|-----------|--------------|---------|-------------|-------------|-----------------|--------------|----------------|--------|
| act-006 | inf-2024-002 | hive-05 | a018 | 3 | 0.9200 | EMERGENCY: Swarm in Progress | high | pending |
| act-007 | inf-2024-002 | hive-05 | a019 | 3 | 0.9200 | Call Emergency Backup | high | pending |
| act-008 | inf-2024-002 | hive-05 | a006 | 3 | 0.9200 | Immediate Hive Inspection | high | pending |
| act-009 | inf-2024-002 | hive-05 | a007 | 3 | 0.9200 | Prepare Swarm Trap | high | pending |
| act-010 | inf-2024-002 | hive-05 | a008 | 3 | 0.9200 | Remove Secondary Swarm Cells | high | pending |
| act-011 | inf-2024-002 | hive-05 | a009 | 3 | 0.9200 | Add Space to Hive | medium | pending |
| act-012 | inf-2024-002 | hive-05 | a011 | 3 | 0.9200 | Document Swarm Event | low | pending |

**Notice:** At 92% confidence, the farmer gets 2 additional EMERGENCY actions plus all the regular swarm actions.

---

### Scenario 3: Pre-Swarm Detection (78%)

**Inference:**
- `inference_id`: inf-2024-003
- `hive_id`: hive-12
- `hive_state`: pre_swarm
- `confidence_score`: 0.7800

**What Happens:**
1. Looks up template_id = 2 (pre_swarm)
2. Queries actions for confidence 0.78
3. Finds actions a001, a002, a003, a005 (but NOT a004 which requires 0.70-0.85)

**Resulting `advisory_actions` records:**

| action_id | inference_id | hive_id | advisory_id | template_id | confidence_score | action_title | priority_level | status |
|-----------|--------------|---------|-------------|-------------|-----------------|--------------|----------------|--------|
| act-013 | inf-2024-003 | hive-12 | a001 | 2 | 0.7800 | Inspect for Overcrowding | high | pending |
| act-014 | inf-2024-003 | hive-12 | a002 | 2 | 0.7800 | Check and Remove Swarm Cells | high | pending |
| act-015 | inf-2024-003 | hive-12 | a003 | 2 | 0.7800 | Ensure Adequate Ventilation | medium | pending |
| act-016 | inf-2024-003 | hive-12 | a005 | 2 | 0.7800 | Schedule Full Inspection | low | pending |

---

## Farmer Workflow

### 1. **Farmer Views Alert**
Query:
```sql
SELECT * FROM alerts WHERE hive_id = 'hive-05' ORDER BY alert_timestamp DESC LIMIT 1;
```

### 2. **Farmer Views Recommended Actions**
Query:
```sql
SELECT 
    aa.action_id,
    aa.action_title,
    aa.action_description,
    aa.priority_level,
    aa.status,
    aa.confidence_score,
    at.hive_state,
    at.severity
FROM advisory_actions aa
JOIN advisory_templates at ON aa.template_id = at.template_id
WHERE aa.inference_id = 'inf-2024-001'
ORDER BY 
    CASE aa.priority_level 
        WHEN 'high' THEN 1 
        WHEN 'medium' THEN 2 
        WHEN 'low' THEN 3 
    END,
    aa.action_order;
```

### 3. **Farmer Completes an Action**
```sql
UPDATE advisory_actions 
SET 
    status = 'completed',
    completed_at = CURRENT_TIMESTAMP,
    notes = 'Added 2 supers, bees have more space now'
WHERE action_id = 'act-001';
```

### 4. **Admin Views All Actions for a Hive**
```sql
SELECT 
    aa.inference_id,
    aa.confidence_score,
    at.hive_state,
    aa.action_title,
    aa.status,
    aa.created_at,
    aa.completed_at
FROM advisory_actions aa
JOIN advisory_templates at ON aa.template_id = at.template_id
WHERE aa.hive_id = 'hive-05'
ORDER BY aa.created_at DESC;
```

---

## Benefits of This Structure

1. **Dynamic Action Selection**: Different actions suggested based on confidence
2. **Reusable Library**: Add/modify actions once, apply to all future inferences
3. **Traceability**: See exactly which actions were suggested for each inference
4. **Farmer Tracking**: Track which actions were completed, skipped, or pending
5. **Analytics**: Analyze which actions are most/least completed
6. **Flexibility**: Easy to add confidence-specific actions (e.g., emergency actions at 90%+)

---

## Migration Steps

1. **Backup existing data**
   ```bash
   pg_dump -h localhost -U postgres -d beehive_db -t advisory_templates -t advisories -t advisory_actions > backup.sql
   ```

2. **Run restructure migration**
   ```bash
   psql -h localhost -U postgres -d beehive_db -f migrations/restructure_advisory_system.sql
   ```

3. **Seed new advisory data**
   ```bash
   psql -h localhost -U postgres -d beehive_db -f migrations/seed_restructured_advisory_data.sql
   ```

4. **Update application code**
   - Replace `api/advisory.py` with `api/advisory_new.py`
   - Update routers to use new structure
   - Update mobile app to display actions from `advisory_actions` table
