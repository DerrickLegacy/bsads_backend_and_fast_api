-- Migration: Add server_url and api_key to users table
-- Date: 2026-05-25
-- Description: Support HTTP API authentication by storing farmer's server credentials at user level

-- Add new columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS server_url VARCHAR(255),
ADD COLUMN IF NOT EXISTS api_key VARCHAR(255);

-- Add comments for documentation
COMMENT ON COLUMN users.server_url IS 'Farmer external data source server URL (e.g., https://abc123.ngrok-free.dev)';
COMMENT ON COLUMN users.api_key IS 'API key for accessing farmer external server';

-- Update existing farmer_data_sources to use http_api instead of ssh
-- This is optional - only run if you want to migrate existing SSH sources
-- UPDATE farmer_data_sources SET source_type = 'http_api' WHERE source_type = 'ssh';
