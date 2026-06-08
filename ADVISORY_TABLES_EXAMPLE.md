# Advisory System Tables - Example Data

## Complete Example: Three Related Tables

---

## Table 1: `advisory_templates` (Classification Definitions)

**Purpose:** Defines each hive state classification - NO actions stored here

| template_id | prediction_code | hive_state | advisory_type | severity | min_confidence_threshold | description |
|-------------|-----------------|------------|---------------|----------|-------------------------|-------------|
| 1 | 0.0 | normal | Reactive | info | 0.6000 | Hive operating normally |
| 2 | 1.0 | pre_swarm | Preventive | high | 0.7000 | Pre-swarm indicators detected |
| 3 | 2.0 | swarm | Reactive | critical | 0.8000 | Active swarm event detected |
| 4 | 3.0 | missing_queen | Reactive | high | 0.7500 | Queen absence suspected |
| 5 | 4.0 | abscondment | Reactive | critical | 0.8500 | Colony has absconded |
| 6 | 5.0 | pest_infested | Reactive | high | 0.7000 | Pest activity detected |

---

## Table 2: `advisories` (Action Library - All Possible Actions)

**Purpose:** Reusable library of ALL possible actions for each classification with confidence thresholds

### Actions for PRE_SWARM (template_id = 2)

| advisory_id | template_id | action_title | action_description | priority_level | confidence_threshold_min | confidence_threshold_max | action_order |
|-------------|-------------|--------------|-------------------|----------------|------------------------|------------------------|-------------|
| a001 | 2 | Inspect for Overcrowding | Check if hive is overcrowded and add supers if needed | high | 0.7000 | 1.0000 | 1 |
| a002 | 2 | Check and Remove Swarm Cells | Inspect frames for swarm cells and remove them | high | 0.7500 | 1.0000 | 2 |
| a003 | 2 | Ensure Adequate Ventilation | Verify proper ventilation | medium | 0.7000 | 1.0000 | 3 |
| a004 | 2 | Monitor Closely | Increase inspection frequency to every 2-3 days | medium | 0.7000 | 0.8500 | 4 |
| a005 | 2 | Schedule Full Inspection | Schedule comprehensive inspection within 48 hours | low | 0.7000 | 1.0000 | 5 |

### Actions for SWARM (template_id = 3)

| advisory_id | template_id | action_title | action_description | priority_level | confidence_threshold_min | confidence_threshold_max | action_order |
|-------------|-------------|--------------|-------------------|----------------|------------------------|------------------------|-------------|
| a006 | 3 | Immediate Hive Inspection | Inspect hive immediately to confirm swarming | high | 0.8000 | 1.0000 | 1 |
| a007 | 3 | Prepare Swarm Trap | Set up swarm trap nearby to capture swarm | high | 0.8000 | 1.0000 | 2 |
| a008 | 3 | Remove Secondary Swarm Cells | Remove remaining swarm cells to prevent secondary swarms | high | 0.8500 | 1.0000 | 3 |
| a009 | 3 | Add Space to Hive | Add supers to provide adequate space | medium | 0.8000 | 1.0000 | 4 |
| a010 | 3 | Contact Beekeeping Association | Reach out for immediate assistance | low | 0.8000 | 0.9000 | 5 |
| a011 | 3 | Document Swarm Event | Record date, weather, and hive status | low | 0.8000 | 1.0000 | 6 |
| a018 | 3 | EMERGENCY: Swarm in Progress | Drop everything and respond immediately | high | 0.9000 | 1.0000 | 1 |
| a019 | 3 | Call Emergency Backup | Contact experienced beekeepers immediately | high | 0.9000 | 1.0000 | 2 |

### Actions for MISSING_QUEEN (template_id = 4)

| advisory_id | template_id | action_title | action_description | priority_level | confidence_threshold_min | confidence_threshold_max | action_order |
|-------------|-------------|--------------|-------------------|----------------|------------------------|------------------------|-------------|
| a012 | 4 | Thorough Frame Inspection | Inspect every frame for queen presence | high | 0.7500 | 1.0000 | 1 |
| a013 | 4 | Check for Fresh Eggs | Look for eggs laid in last 3 days | high | 0.7500 | 1.0000 | 2 |
| a014 | 4 | Inspect for Emergency Queen Cells | Check for emergency queen cells on frame faces | medium | 0.7500 | 1.0000 | 3 |
| a015 | 4 | Introduce Mated Queen | Introduce new queen if absent for 3+ days | high | 0.8000 | 1.0000 | 4 |
| a016 | 4 | Monitor Daily for 7 Days | Check hive daily for next week | medium | 0.7500 | 1.0000 | 5 |

### Actions for PEST_INFESTED (template_id = 6)

| advisory_id | template_id | action_title | action_description | priority_level | confidence_threshold_min | confidence_threshold_max | action_order |
|-------------|-------------|--------------|-------------------|----------------|------------------------|------------------------|-------------|
| a025 | 6 | Identify Pest Type | Inspect to identify specific pest type | high | 0.7000 | 1.0000 | 1 |
| a026 | 6 | Apply Appropriate Treatment | Use correct treatment for identified pest | high | 0.7500 | 1.0000 | 2 |
| a027 | 6 | Clean Hive Bottom Board | Remove debris and pest larvae | medium | 0.7000 | 1.0000 | 3 |
| a028 | 6 | Strengthen Colony | Ensure colony is well-fed and strong | medium | 0.7000 | 1.0000 | 4 |
| a029 | 6 | Follow-up Inspection | Re-inspect after 7 days to verify treatment | medium | 0.7000 | 1.0000 | 5 |
| a030 | 6 | Install Pest Prevention | Add traps, screens, or entrance reducers | low | 0.7000 | 1.0000 | 6 |

---

## Table 3: `advisory_actions` (Actual Actions Suggested Per Inference)

**Purpose:** Records which actions were actually suggested for each hive inference based on confidence score

### Example 1: Hive-05 Swarm Detection at 85% Confidence

**Inference:** `inference_id = inf-2024-001`, `hive_id = hive-05`, `confidence = 0.85`

| action_id | inference_id | hive_id | advisory_id | template_id | confidence_score | action_title | priority_level | status | completed_at | notes |
|-----------|--------------|---------|-------------|-------------|-----------------|--------------|----------------|--------|-------------|-------|
| act-001 | inf-2024-001 | hive-05 | a006 | 3 | 0.8500 | Immediate Hive Inspection | high | completed | 2026-06-08 10:30 | Found swarm on nearby tree |
| act-002 | inf-2024-001 | hive-05 | a007 | 3 | 0.8500 | Prepare Swarm Trap | high | completed | 2026-06-08 11:00 | Trap set with lemongrass |
| act-003 | inf-2024-001 | hive-05 | a008 | 3 | 0.8500 | Remove Secondary Swarm Cells | high | pending | NULL | NULL |
| act-004 | inf-2024-001 | hive-05 | a009 | 3 | 0.8500 | Add Space to Hive | medium | completed | 2026-06-08 11:30 | Added 2 supers |
| act-005 | inf-2024-001 | hive-05 | a011 | 3 | 0.8500 | Document Swarm Event | low | completed | 2026-06-08 12:00 | Logged in notebook |

**Notice:** 
- Actions a018 and a019 are NOT included (they need 90%+ confidence)
- Action a010 is NOT included (confidence range 0.80-0.90, excluded at exactly 0.85)
- Farmer has completed 4 out of 5 actions

---

### Example 2: Hive-05 Swarm Detection at 92% Confidence (Same hive, later)

**Inference:** `inference_id = inf-2024-002`, `hive_id = hive-05`, `confidence = 0.92`

| action_id | inference_id | hive_id | advisory_id | template_id | confidence_score | action_title | priority_level | status | completed_at | notes |
|-----------|--------------|---------|-------------|-------------|-----------------|--------------|----------------|--------|-------------|-------|
| act-006 | inf-2024-002 | hive-05 | a018 | 3 | 0.9200 | EMERGENCY: Swarm in Progress | high | completed | 2026-06-10 09:05 | Responded immediately |
| act-007 | inf-2024-002 | hive-05 | a019 | 3 | 0.9200 | Call Emergency Backup | high | completed | 2026-06-10 09:06 | Called John, he came over |
| act-008 | inf-2024-002 | hive-05 | a006 | 3 | 0.9200 | Immediate Hive Inspection | high | completed | 2026-06-10 09:20 | Active swarm confirmed |
| act-009 | inf-2024-002 | hive-05 | a007 | 3 | 0.9200 | Prepare Swarm Trap | high | completed | 2026-06-10 09:30 | Used existing trap |
| act-010 | inf-2024-002 | hive-05 | a008 | 3 | 0.9200 | Remove Secondary Swarm Cells | high | pending | NULL | NULL |
| act-011 | inf-2024-002 | hive-05 | a009 | 3 | 0.9200 | Add Space to Hive | medium | pending | NULL | NULL |
| act-012 | inf-2024-002 | hive-05 | a011 | 3 | 0.9200 | Document Swarm Event | low | skipped | NULL | Too urgent, skipped docs |

**Notice:** 
- At 92% confidence, farmer gets 7 actions instead of 5
- EMERGENCY actions (a018, a019) are now included
- More urgent response required

---

### Example 3: Hive-12 Pre-Swarm Detection at 73% Confidence

**Inference:** `inference_id = inf-2024-003`, `hive_id = hive-12`, `confidence = 0.73`

| action_id | inference_id | hive_id | advisory_id | template_id | confidence_score | action_title | priority_level | status | completed_at | notes |
|-----------|--------------|---------|-------------|-------------|-----------------|--------------|----------------|--------|-------------|-------|
| act-013 | inf-2024-003 | hive-12 | a001 | 2 | 0.7300 | Inspect for Overcrowding | high | completed | 2026-06-08 14:00 | Not overcrowded yet |
| act-014 | inf-2024-003 | hive-12 | a003 | 2 | 0.7300 | Ensure Adequate Ventilation | medium | completed | 2026-06-08 14:15 | Added ventilation holes |
| act-015 | inf-2024-003 | hive-12 | a004 | 2 | 0.7300 | Monitor Closely | medium | in_progress | NULL | Checking every 2 days |
| act-016 | inf-2024-003 | hive-12 | a005 | 2 | 0.7300 | Schedule Full Inspection | low | pending | NULL | NULL |

**Notice:**
- Action a002 is NOT included (needs 75%+ confidence)
- Only 4 actions suggested for pre-swarm at 73%
- Lower severity than full swarm

---

### Example 4: Hive-18 Missing Queen at 88% Confidence

**Inference:** `inference_id = inf-2024-004`, `hive_id = hive-18`, `confidence = 0.88`

| action_id | inference_id | hive_id | advisory_id | template_id | confidence_score | action_title | priority_level | status | completed_at | notes |
|-----------|--------------|---------|-------------|-------------|-----------------|--------------|----------------|--------|-------------|-------|
| act-017 | inf-2024-004 | hive-18 | a012 | 4 | 0.8800 | Thorough Frame Inspection | high | completed | 2026-06-09 08:00 | Could not find queen |
| act-018 | inf-2024-004 | hive-18 | a013 | 4 | 0.8800 | Check for Fresh Eggs | high | completed | 2026-06-09 08:15 | No eggs found |
| act-019 | inf-2024-004 | hive-18 | a014 | 4 | 0.8800 | Inspect for Emergency Queen Cells | medium | completed | 2026-06-09 08:30 | Found 3 queen cells |
| act-020 | inf-2024-004 | hive-18 | a015 | 4 | 0.8800 | Introduce Mated Queen | high | pending | NULL | Ordered queen, arriving Friday |
| act-021 | inf-2024-004 | hive-18 | a016 | 4 | 0.8800 | Monitor Daily for 7 Days | medium | in_progress | NULL | Day 3 of monitoring |

**Notice:**
- All 5 actions for missing_queen are included (confidence 88% is high)
- Farmer is actively working through the checklist
- Some actions depend on others (can't introduce queen until it arrives)

---

## How It Works: Confidence-Based Selection

### Query Logic (from advisory_new.py)

```sql
SELECT * FROM advisories 
WHERE template_id = 3  -- swarm
  AND is_active = TRUE
  AND confidence_threshold_min <= 0.85  -- inference confidence
  AND confidence_threshold_max >= 0.85
ORDER BY action_order;
```

### Confidence Scenarios for SWARM

| Confidence | Actions Included | Count |
|------------|------------------|-------|
| 79% | None (below 80% threshold) | 0 |
| 82% | a006, a007, a009, a010, a011 | 5 |
| 85% | a006, a007, a009, a011 | 4 |
| 87% | a006, a007, a008, a009, a011 | 5 |
| 92% | a018, a019, a006, a007, a008, a009, a011 | 7 |
| 95% | a018, a019, a006, a007, a008, a009, a011 | 7 |

### Key Points

1. **Different confidence = different actions**: Higher confidence triggers more/different actions
2. **Threshold ranges are flexible**: Can overlap or be exclusive
3. **Emergency actions**: Can be configured for very high confidence (90%+)
4. **Lower confidence exclusions**: Some actions require higher confidence (a002 needs 75%+)
5. **Action library is reusable**: Same actions used for all hives, but selected per inference

---

## Relationships

```
advisory_templates (1) ──────→ (many) advisories
                                          ↓
                                    (references)
                                          ↓
inference_results (1) ──────→ (many) advisory_actions
```

**Flow:**
1. ML model creates `InferenceResult` with confidence score
2. System looks up `AdvisoryTemplate` by `hive_state`
3. Queries `advisories` matching template and confidence range
4. Creates `AdvisoryAction` records for that specific inference
5. Farmer sees personalized action checklist for their hive
