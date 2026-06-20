-- Migration: Add admin_keys table
-- Created: 2024-01-01
-- Description: Creates the admin_keys table for storing admin keys for external data source servers

-- Create admin_keys table
CREATE TABLE IF NOT EXISTS admin_keys (
    admin_key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_name VARCHAR(100) NOT NULL,
    server_url VARCHAR(255),
    admin_key VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index on server_name for faster lookups
CREATE INDEX IF NOT EXISTS idx_admin_keys_server_name ON admin_keys(server_name);

-- Create index on is_active for filtering active keys
CREATE INDEX IF NOT EXISTS idx_admin_keys_is_active ON admin_keys(is_active);

-- Add comment to table
COMMENT ON TABLE admin_keys IS 'Stores admin keys for external data source servers used to generate farmer API tokens';

-- Add comments to columns
COMMENT ON COLUMN admin_keys.admin_key_id IS 'Unique identifier for the admin key record';
COMMENT ON COLUMN admin_keys.server_name IS 'Human-readable name for the server (e.g., "Farmer Data Source Simulation")';
COMMENT ON COLUMN admin_keys.server_url IS 'Base URL of the external server';
COMMENT ON COLUMN admin_keys.admin_key IS 'The actual admin key used to authenticate with the external server';
COMMENT ON COLUMN admin_keys.description IS 'Optional description of the key and its purpose';
COMMENT ON COLUMN admin_keys.is_active IS 'Whether this key is currently active';
COMMENT ON COLUMN admin_keys.created_by IS 'User ID of the admin who created this key (NULL for system-created keys)';
COMMENT ON COLUMN admin_keys.created_at IS 'Timestamp when the key was created';
COMMENT ON COLUMN admin_keys.updated_at IS 'Timestamp when the key was last updated';
