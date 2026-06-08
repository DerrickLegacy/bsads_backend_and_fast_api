-- ============================================================================
-- Migration: Restructure Advisory System
-- ============================================================================
-- Purpose:
--   1. advisory_templates: Classification definitions only (no actions)
--   2. advisories: Reusable action library for each classification
--   3. advisory_actions: Specific actions chosen per inference based on threshold
-- ============================================================================

BEGIN;

-- Step 1: Backup existing data (optional safety measure)
CREATE TABLE IF NOT EXISTS advisory_templates_backup AS SELECT * FROM advisory_templates;
CREATE TABLE IF NOT EXISTS advisories_backup AS SELECT * FROM advisories;
CREATE TABLE IF NOT EXISTS advisory_actions_backup AS SELECT * FROM advisory_actions;

-- Step 2: Drop existing foreign key constraints
ALTER TABLE advisories DROP CONSTRAINT IF EXISTS advisories_template_id_fkey;
ALTER TABLE advisory_actions DROP CONSTRAINT IF EXISTS advisory_actions_advisory_id_fkey;
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_advisory_id_fkey;

-- Step 3: Drop existing relationships
DROP TABLE IF EXISTS advisory_actions CASCADE;
DROP TABLE IF EXISTS advisories CASCADE;

-- Step 4: Modify advisory_templates to be classification-only
-- Remove advisory_text column and add threshold columns
ALTER TABLE advisory_templates DROP COLUMN IF EXISTS advisory_text;
ALTER TABLE advisory_templates DROP COLUMN IF EXISTS condition_label;
ALTER TABLE advisory_templates ADD COLUMN IF NOT EXISTS min_confidence_threshold NUMERIC(5, 4) DEFAULT 0.70;
ALTER TABLE advisory_templates ADD COLUMN IF NOT EXISTS description TEXT;

COMMENT ON TABLE advisory_templates IS 'Classification definitions for hive states';
COMMENT ON COLUMN advisory_templates.hive_state IS 'Unified hive state vocabulary (e.g., swarm, pre_swarm, missing_queen)';
COMMENT ON COLUMN advisory_templates.prediction_code IS 'Numeric code from ML model';
COMMENT ON COLUMN advisory_templates.advisory_type IS 'Preventive or Reactive';
COMMENT ON COLUMN advisory_templates.severity IS 'info, high, critical';
COMMENT ON COLUMN advisory_templates.min_confidence_threshold IS 'Minimum confidence score required to trigger actions';
COMMENT ON COLUMN advisory_templates.description IS 'Brief description of this classification';

-- Step 5: Create new advisories table as ACTION LIBRARY
CREATE TABLE advisories (
    advisory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id BIGINT NOT NULL REFERENCES advisory_templates(template_id) ON DELETE CASCADE,
    action_title VARCHAR(200) NOT NULL,
    action_description TEXT NOT NULL,
    priority_level VARCHAR(20) NOT NULL DEFAULT 'medium', -- high, medium, low
    confidence_threshold_min NUMERIC(5, 4) NOT NULL DEFAULT 0.70,
    confidence_threshold_max NUMERIC(5, 4) NOT NULL DEFAULT 1.00,
    action_order INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_advisories_template_id ON advisories(template_id);
CREATE INDEX idx_advisories_confidence_range ON advisories(confidence_threshold_min, confidence_threshold_max);

COMMENT ON TABLE advisories IS 'Reusable action library - all possible actions for each classification';
COMMENT ON COLUMN advisories.action_title IS 'Short title for the action';
COMMENT ON COLUMN advisories.action_description IS 'Detailed description of what to do';
COMMENT ON COLUMN advisories.confidence_threshold_min IS 'Minimum confidence score to suggest this action';
COMMENT ON COLUMN advisories.confidence_threshold_max IS 'Maximum confidence score for this action';
COMMENT ON COLUMN advisories.action_order IS 'Display order for actions';

-- Step 6: Create new advisory_actions table for ACTUAL SUGGESTED ACTIONS PER INFERENCE
CREATE TABLE advisory_actions (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inference_id UUID NOT NULL REFERENCES inference_results(inference_id) ON DELETE CASCADE,
    hive_id UUID NOT NULL REFERENCES hives(hive_id) ON DELETE CASCADE,
    advisory_id UUID NOT NULL REFERENCES advisories(advisory_id) ON DELETE CASCADE,
    template_id BIGINT NOT NULL REFERENCES advisory_templates(template_id) ON DELETE CASCADE,
    confidence_score NUMERIC(5, 4) NOT NULL,
    action_title VARCHAR(200) NOT NULL,
    action_description TEXT NOT NULL,
    priority_level VARCHAR(20) NOT NULL DEFAULT 'medium',
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, in_progress, completed, skipped
    completed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_advisory_actions_inference_id ON advisory_actions(inference_id);
CREATE INDEX idx_advisory_actions_hive_id ON advisory_actions(hive_id);
CREATE INDEX idx_advisory_actions_template_id ON advisory_actions(template_id);
CREATE INDEX idx_advisory_actions_status ON advisory_actions(status);

COMMENT ON TABLE advisory_actions IS 'Specific actions suggested for each hive inference based on confidence threshold';
COMMENT ON COLUMN advisory_actions.inference_id IS 'Which ML inference triggered this action';
COMMENT ON COLUMN advisory_actions.hive_id IS 'Which hive this action is for';
COMMENT ON COLUMN advisory_actions.advisory_id IS 'References the action template from advisories table';
COMMENT ON COLUMN advisory_actions.confidence_score IS 'ML model confidence score for this inference';
COMMENT ON COLUMN advisory_actions.status IS 'Farmer action status: pending, in_progress, completed, skipped';

-- Step 7: Update alerts table to remove direct advisory_id link
-- Alerts now link to inference, and actions are retrieved via inference_id
ALTER TABLE alerts DROP COLUMN IF EXISTS advisory_id;

-- Step 8: Add trigger to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_advisories_updated_at BEFORE UPDATE ON advisories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_advisory_actions_updated_at BEFORE UPDATE ON advisory_actions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;
