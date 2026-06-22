# Prediction Details Format

## Overview

When the ML model classifies hive audio, it returns confidence scores for all possible classes. The full prediction details are now stored in the `inference_results.prediction_details` JSONB column and returned in alert responses.

## Database Storage

**Table**: `inference_results`  
**Column**: `prediction_details` (JSONB)

### JSON Structure

```json
{
  "predicted_class": "external_noise",
  "confidence": 1.0,
  "top_predictions": [
    {
      "class": "external_noise",
      "confidence": 1.0
    },
    {
      "class": "inactive_hive",
      "confidence": 0.0
    },
    {
      "class": "pests",
      "confidence": 0.0
    }
  ]
}
```

### Fields

- **predicted_class** (string): The primary classification result (normalized to database vocabulary)
- **confidence** (float): Confidence score for the predicted class (0.0 - 1.0)
- **top_predictions** (array): Top 3 predictions sorted by confidence descending
  - **class** (string): Class name (normalized)
  - **confidence** (float): Confidence score (0.0 - 1.0)

### Possible Classes

The system uses these normalized class names:

| ML Model Label | Normalized Class | Description |
|---|---|---|
| `swarming` | `swarming` | Bees are swarming |
| `absconding` | `absconding` | Bees are abandoning hive |
| `missing_queen` | `missing_queen` | Queen bee is missing |
| `queenbee_present` | `queenbee_present` | Queen bee is healthy |
| `pests` | `pests` | Pest infestation detected |
| `external_noise` | `external_noise` | External environmental noise |
| `inactive_hive` | `inactive_hive` | No bee activity detected |
| `uncertain` | `uncertain` | Model is uncertain |

## API Response

### Alert Detail Endpoint

**GET** `/api/mobile/alerts/{alert_id}`

**Response includes**:

```json
{
  "id": "alert-uuid",
  "hive_id": "hive-uuid",
  "hive_name": "Hive 01",
  "severity": "high",
  "title": "Swarming Detected",
  "details": "...",
  "prediction_details": {
    "predicted_class": "swarming",
    "confidence": 0.95,
    "top_predictions": [
      {
        "class": "swarming",
        "confidence": 0.95
      },
      {
        "class": "queenbee_present",
        "confidence": 0.03
      },
      {
        "class": "external_noise",
        "confidence": 0.02
      }
    ]
  },
  "audio_recording": {...},
  "advisory": {...}
}
```

## Example ML Model Output

From the inference engine:

```
🎵 Prediction for audio_123.wav:
Predicted Class: external_noise
Confidence: 100.00%
Top-3 Predictions:
  external_noise: 100.00%
  inactive_hive: 0.00%
  pests: 0.00%
```

This gets stored as:

```json
{
  "predicted_class": "external_noise",
  "confidence": 1.0,
  "top_predictions": [
    {"class": "external_noise", "confidence": 1.0},
    {"class": "inactive_hive", "confidence": 0.0},
    {"class": "pests", "confidence": 0.0}
  ]
}
```

## Use Cases

### 1. Display Confidence Levels
Show users how confident the model is about predictions:
- **High confidence** (>0.9): Strong detection, immediate action
- **Medium confidence** (0.7-0.9): Likely detection, monitor closely
- **Low confidence** (<0.7): Uncertain, verify manually

### 2. Alternative Diagnoses
Show top-3 predictions to give context:
```
Primary: Swarming (95%)
Also possible:
- Queen Present (3%)
- External Noise (2%)
```

### 3. Model Performance Tracking
Query prediction_details to analyze:
- Prediction confidence distribution
- Most common alternative predictions
- Model uncertainty patterns

### 4. Multi-Label Context
Even when one class dominates, seeing other predictions helps understand edge cases:
```
Predicted: External Noise (100%)
Alternatives: Inactive Hive (0%), Pests (0%)

→ Indicates very clear external interference, not ambiguous
```

## Database Queries

### Get all high-confidence swarming predictions
```sql
SELECT 
  inference_id,
  hive_id,
  prediction_details->>'predicted_class' as predicted_class,
  (prediction_details->>'confidence')::float as confidence
FROM inference_results
WHERE prediction_details->>'predicted_class' = 'swarming'
  AND (prediction_details->>'confidence')::float > 0.9;
```

### Get predictions with low confidence (uncertain)
```sql
SELECT 
  inference_id,
  hive_id,
  prediction_details
FROM inference_results
WHERE (prediction_details->>'confidence')::float < 0.7;
```

### Get all predictions for a specific class in top-3
```sql
SELECT 
  inference_id,
  hive_id,
  prediction_details
FROM inference_results
WHERE prediction_details @> '{"top_predictions": [{"class": "pests"}]}';
```

## Migration

**File**: `api/migrations/004_add_prediction_details_to_inference.sql`

Adds the `prediction_details` JSONB column with GIN index for efficient querying.

## Implementation Notes

1. **Backward Compatibility**: Existing inference records will have `NULL` in `prediction_details` - this is handled gracefully
2. **Performance**: GIN index enables fast JSON queries on prediction details
3. **Normalization**: All class names are normalized using `normalize_hive_state()` function
4. **Top-3 Limit**: Only top 3 predictions are stored to keep data size reasonable
5. **Confidence Format**: Stored as float (0.0-1.0), displayed as percentage (0-100%)

## Testing

After deploying, verify with:

```bash
# Check a recent inference result
PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db \
  -c "SELECT inference_id, hive_state, confidence_score, prediction_details 
      FROM inference_results 
      ORDER BY created_at DESC 
      LIMIT 1;"
```

Expected output should show the full prediction_details JSON.

---

**Last Updated**: June 22, 2026  
**Version**: 1.0
