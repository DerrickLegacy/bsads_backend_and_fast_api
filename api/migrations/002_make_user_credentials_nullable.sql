-- Migration: Make server_url and api_key nullable in users table
-- Created: 2024-01-01
-- Description: Allows farmers to register without tokens, which admins assign later

-- Make server_url and api_key nullable
ALTER TABLE users ALTER COLUMN server_url DROP NOT NULL;
ALTER TABLE users ALTER COLUMN api_key DROP NOT NULL;

-- Add comments to clarify the new workflow
COMMENT ON COLUMN users.server_url IS 'External data source server URL (assigned by admin after registration)';
COMMENT ON COLUMN users.api_key IS 'API key for accessing farmer data source server (assigned by admin after registration)';
