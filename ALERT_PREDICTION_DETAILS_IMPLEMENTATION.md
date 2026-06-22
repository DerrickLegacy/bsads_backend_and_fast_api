# Alert Prediction Details Implementation

## Summary

The alert system now stores and returns complete ML model prediction details, including the predicted class, confidence score, and top-3 alternative predictions with their confidence scores.

## Changes Made

### 1. Database Schema Update

**File**: `api/migrations/004_add_prediction_details_to_inference.sql`

- Added `prediction_details` JSONB column to `inference_results` table
- Created GIN index for efficient JSON querying
- Added column comment documentation

**Run Migration**:
```bash
PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db \
  -f api/migrations/004_add_prediction_details_to_inference.sql
```

### 2. Model Updates

**File**: `api/models.py`

Updated `InferenceResult` model:
```python
class InferenceResult(Base):
    # ... existing fields
    prediction_details = Column(JSONB, nullable=True)  # NEW
```

### 3. Inference Engine Updates

**File**: `api/inference_engine.py`

Updated `PredictionResult` dataclass to capture all scores:
```python
@dataclass
class PredictionResult:
    label: str
    confidence: float
    latency_ms: int
    all_scores: dict  # NEW - captures all class predictions
```

Updated `predict_from_bytes()` to extract all_scores from HF API response:
```python
return PredictionResult(
    label=result["label"],
    confidence=float(result["score"]),
    latency_ms=latency_ms,
    all_scores=result.get("all_scores", {}),  # NEW
)
```

### 4. Processing Logic Updates

**File**: `api/processing.py`

Updated `process_audio_file()` to build and store prediction details:
```python
# Build prediction details with top-3 predictions
sorted_predictions = sorted(
    result.all_scores.items(), 
    key=lambda x: x[1], 
    reverse=True
)[:3]

prediction_details = {
    "predicted_class": hive_state,
    "confidence": float(result.confidence),
    "top_predictions": [
        {
            "class": normalize_hive_state(class_name),
            "confidence": float(conf)
        }
        for class_name, conf in sorted_predictions
    ]
}

inference = InferenceResult(
    # ... existing fields
    prediction_details=prediction_details,  # NEW
)
```

### 5. API Schema Updates

**File**: `api/schemas.py`

Updated `MobileAlertDetailResponse`:
```python
class MobileAlertDetailResponse(BaseModel):
    # ... existing fields
    prediction_details: Optional[dict] = None  # NEW
```

### 6. Alert Endpoint Updates

**File**: `api/routers/alerts.py`

Updated `_to_mobile_detail()` function to fetch and return prediction details:
```python
def _to_mobile_detail(alert: Alert, db: Session) -> MobileAlertDetailResponse:
    # ... existing code
    
    # Get inference result for prediction details
    prediction_details = None
    if alert.inference_id:
        inference = db.query(InferenceResult).filter(
            InferenceResult.inference_id == alert.inference_id
        ).first()
        
        if inference and inference.prediction_details:
            prediction_details = inference.prediction_details
    
    # ... existing code
    
    return MobileAlertDetailResponse(
        # ... existing fields
        prediction_details=prediction_details,  # NEW
    )
```

## Data Format

### Stored in Database (JSONB)

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

### Returned in API Response

**Endpoint**: `GET /api/mobile/alerts/{alert_id}`

```json
{
  "id": "alert-uuid",
  "hive_id": "hive-uuid",
  "hive_name": "Hive 01",
  "severity": "high",
  "title": "Swarming Detected",
  "time": "2026-06-22T10:30:00",
  "details": "Immediate action required...",
  "acknowledged": false,
  "prediction_details": {
    "predicted_class": "swarming",
    "confidence": 0.95,
    "top_predictions": [
      {"class": "swarming", "confidence": 0.95},
      {"class": "queenbee_present", "confidence": 0.03},
      {"class": "external_noise", "confidence": 0.02}
    ]
  },
  "audio_recording": {...},
  "advisory": {...}
}
```

## Benefits

### 1. **Transparency**
Users can see not just the prediction, but how confident the model is and what other possibilities exist.

### 2. **Context for Decision Making**
Example: If model predicts "swarming" at 95% with next closest at 3%, it's very clear. If it's 60% swarming, 35% external_noise, user should verify.

### 3. **Model Performance Tracking**
Analytics can track:
- Average confidence scores
- Distribution of predictions
- How often model is uncertain

### 4. **Better User Experience**
Mobile app can display:
```
🔴 High Alert: Swarming Detected
Confidence: 95%

Alternative Possibilities:
✓ Queen Present (3%)
✓ External Noise (2%)
```

## Testing

### 1. Verify Database Structure
```bash
PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db \
  -c "\d inference_results"
```

Should show `prediction_details | jsonb` column.

### 2. Check Existing Data
```bash
PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db \
  -c "SELECT inference_id, hive_state, confidence_score, prediction_details 
      FROM inference_results 
      ORDER BY created_at DESC 
      LIMIT 3;"
```

Older records will have `NULL` prediction_details (expected).  
New inferences will have the full JSON structure.

### 3. Test API Endpoint
```bash
# Get an alert ID first
ALERT_ID=$(PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -t \
  -c "SELECT alert_id FROM alerts ORDER BY created_at DESC LIMIT 1;")

# Test the endpoint (requires auth token)
curl -X GET "http://localhost:8003/api/mobile/alerts/${ALERT_ID}" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Response should include `prediction_details` field.

### 4. Process New Audio
When the poller processes new audio files, the inference results will automatically include prediction_details.

Monitor logs:
```bash
cd ~/Desktop/final_year_project/combo2/bsads_backend_and_fast_api
source venv/bin/activate
python3 test_poller_manual.py
```

## Backward Compatibility

✅ **Fully Backward Compatible**

- Existing inference records have `NULL` in `prediction_details` - handled gracefully
- API returns `null` for prediction_details when not available
- No breaking changes to existing endpoints
- New field is optional in response schema

## Files Modified

1. `api/models.py` - Added prediction_details column
2. `api/schemas.py` - Added prediction_details to response schema
3. `api/inference_engine.py` - Capture all_scores from ML model
4. `api/processing.py` - Build and store prediction details
5. `api/routers/alerts.py` - Return prediction details in response
6. `api/migrations/004_add_prediction_details_to_inference.sql` - Database migration

## Files Created

1. `PREDICTION_DETAILS_FORMAT.md` - Complete format documentation
2. `ALERT_PREDICTION_DETAILS_IMPLEMENTATION.md` - This file

## Next Steps

1. ✅ Database migration applied
2. ✅ Code changes completed
3. ✅ Documentation created
4. ⏳ Restart backend API for changes to take effect
5. ⏳ Run audio poller to generate new inferences with prediction details
6. ⏳ Test mobile app to verify prediction_details display

## Deployment

### Backend API
```bash
# Stop current backend
pkill -f "uvicorn api.main:app"

# Restart with new code
cd ~/Desktop/final_year_project/combo2/bsads_backend_and_fast_api
source venv/bin/activate
uvicorn api.main:app --reload --port 8003
```

### Verify
```bash
# Check API is running
curl http://localhost:8003/health

# Process some audio
python3 test_poller_manual.py

# Check for new inferences with prediction_details
PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db \
  -c "SELECT prediction_details FROM inference_results 
      WHERE prediction_details IS NOT NULL 
      LIMIT 1;"
```

## Expected Output Example

From ML model logs:
```
🎵 Prediction for audio_xyz.wav:
Predicted Class: external_noise
Confidence: 100.00%
Top-3 Predictions:
  external_noise: 100.00%
  inactive_hive: 0.00%
  pests: 0.00%
```

Stored in database:
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

Returned to mobile app:
```json
{
  "prediction_details": {
    "predicted_class": "external_noise",
    "confidence": 1.0,
    "top_predictions": [...]
  }
}
```

---

**Implementation Date**: June 22, 2026  
**Status**: ✅ Complete  
**Version**: 1.0
