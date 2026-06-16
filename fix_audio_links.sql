-- Fix missing audio_id links in inference_results
-- This links inferences to their corresponding audio sources by matching timestamps

-- Update inference_results by finding the most recent audio source for each hive
-- that was processed around the same time as the inference
UPDATE inference_results ir
SET audio_id = (
    SELECT au.audio_id
    FROM audio_sources au
    WHERE au.hive_id = ir.hive_id
      AND au.status = 'processed'
      AND au.audio_id IS NOT NULL
      -- Find audio processed within 5 minutes of the inference
      AND ABS(EXTRACT(EPOCH FROM (au.updated_at - ir.analyzed_at))) < 300
    ORDER BY ABS(EXTRACT(EPOCH FROM (au.updated_at - ir.analyzed_at)))
    LIMIT 1
)
WHERE ir.audio_id IS NULL
  AND ir.analyzed_at >= CURRENT_DATE - INTERVAL '7 days';  -- Only fix recent records

-- Show results
SELECT 
    COUNT(*) as total_inferences,
    COUNT(audio_id) as linked_to_audio,
    COUNT(*) - COUNT(audio_id) as missing_audio_link
FROM inference_results
WHERE analyzed_at >= CURRENT_DATE - INTERVAL '7 days';
