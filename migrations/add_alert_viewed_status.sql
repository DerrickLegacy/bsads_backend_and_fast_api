-- ============================================================================
-- Migration: Add viewed status to alerts
-- ============================================================================
-- Purpose: Track when farmers view alerts in the mobile app
-- ============================================================================

BEGIN;

-- Add viewed_at timestamp column
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS viewed_at TIMESTAMP;

-- Add index for querying unviewed alerts
CREATE INDEX IF NOT EXISTS idx_alerts_viewed_at ON alerts(viewed_at) WHERE viewed_at IS NULL;

-- Add comments
COMMENT ON COLUMN alerts.viewed_at IS 'Timestamp when farmer first viewed this alert in the app';

COMMIT;
