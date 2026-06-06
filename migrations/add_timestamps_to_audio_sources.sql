-- Migration: Add created_at and updated_at to audio_sources table
-- Date: 2026-06-06
-- Description: Add timestamp tracking columns to audio_sources for better auditing

-- Add timestamp columns if they don't exist
ALTER TABLE audio_sources 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Backfill existing rows with ingestion_timestamp value
UPDATE audio_sources 
SET created_at = ingestion_timestamp, 
    updated_at = ingestion_timestamp
WHERE created_at IS NULL;

-- Add comments for documentation
COMMENT ON COLUMN audio_sources.created_at IS 'Timestamp when the record was created';
COMMENT ON COLUMN audio_sources.updated_at IS 'Timestamp when the record was last updated';
