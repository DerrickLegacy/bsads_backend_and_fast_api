-- Migration: Add push_notification_devices table
-- Date: 2026-06-19
-- Description: Store push notification device registrations for Expo Push API

CREATE TABLE IF NOT EXISTS push_notification_devices (
    id         BIGSERIAL PRIMARY KEY,
    user_id    UUID NOT NULL,
    token      VARCHAR(500) NOT NULL,
    device_id  VARCHAR(255) NOT NULL,
    platform   VARCHAR(50) NOT NULL,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_push_devices_user FOREIGN KEY (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_push_devices_user_id ON push_notification_devices(user_id);

COMMENT ON TABLE push_notification_devices IS 'Push notification device registrations for Expo Push API';
COMMENT ON COLUMN push_notification_devices.user_id IS 'ID of the user who owns this device';
COMMENT ON COLUMN push_notification_devices.token IS 'Expo push token';
COMMENT ON COLUMN push_notification_devices.device_id IS 'Unique device identifier';
COMMENT ON COLUMN push_notification_devices.platform IS 'Device platform (e.g., ios, android)';
COMMENT ON COLUMN push_notification_devices.is_active IS 'Whether this device is active and should receive notifications';
