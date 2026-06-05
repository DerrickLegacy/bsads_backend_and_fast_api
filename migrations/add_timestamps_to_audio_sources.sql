-- Migration: Add created_at and updated_at to audio_sources
-- Date: 2026-06-05
-- Description: Align audio_sources with Beehive DB schema

ALTER TABLE audio_sources
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Backfill created_at from ingestion_timestamp where available
UPDATE audio_sources
SET created_at = ingestion_timestamp
WHERE ingestion_timestamp IS NOT NULL AND created_at IS NULL;

COMMENT ON COLUMN audio_sources.created_at IS 'Row creation timestamp';
COMMENT ON COLUMN audio_sources.updated_at IS 'Row last updated timestamp';
