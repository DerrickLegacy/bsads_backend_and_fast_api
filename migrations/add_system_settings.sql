-- Migration: Add system_settings table
-- Date: 2026-06-05
-- Description: Key-value store for app-wide configuration settings

CREATE TABLE IF NOT EXISTS system_settings (
    id         BIGSERIAL PRIMARY KEY,
    key        VARCHAR NOT NULL,
    value      TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT system_settings_key_key UNIQUE (key)
);

COMMENT ON TABLE system_settings IS 'App-wide key-value configuration store';
COMMENT ON COLUMN system_settings.key IS 'Unique setting name';
COMMENT ON COLUMN system_settings.value IS 'Setting value (stored as text)';
