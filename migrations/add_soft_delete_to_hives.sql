-- Migration: Add soft delete to hives table
-- Date: 2026-05-25
-- Description: Add is_deleted and deleted_at columns for soft delete functionality

-- Add soft delete columns to hives table
ALTER TABLE hives 
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_hives_is_deleted ON hives(is_deleted);

-- Add comments for documentation
COMMENT ON COLUMN hives.is_deleted IS 'Soft delete flag - true if hive has been deleted';
COMMENT ON COLUMN hives.deleted_at IS 'Timestamp when hive was soft deleted';
