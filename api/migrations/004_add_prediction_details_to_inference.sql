-- Migration: Add prediction_details column to inference_results table
-- Purpose: Store full ML model prediction details (top-3 predictions with confidence scores)
-- Date: 2026-06-22

-- Add prediction_details column to store JSON object with prediction data
ALTER TABLE inference_results 
ADD COLUMN IF NOT EXISTS prediction_details JSONB;

-- Add comment to document the column structure
COMMENT ON COLUMN inference_results.prediction_details IS 
'Stores ML model prediction details as JSON: 
{
  "predicted_class": "external_noise",
  "confidence": 1.0,
  "top_predictions": [
    {"class": "external_noise", "confidence": 1.0},
    {"class": "inactive_hive", "confidence": 0.0},
    {"class": "pests", "confidence": 0.0}
  ]
}';

-- Create index for querying by predicted class (if needed for analytics)
CREATE INDEX IF NOT EXISTS idx_inference_prediction_details 
ON inference_results USING gin(prediction_details);
