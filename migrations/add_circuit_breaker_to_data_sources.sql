-- Migration: Add circuit breaker timestamp to farmer_data_sources
-- Purpose: Track connection failures to avoid repeatedly hammering unreachable APIs
-- Date: 2026-06-17

ALTER TABLE farmer_data_sources
ADD COLUMN IF NOT EXISTS last_error_at TIMESTAMP NULL;

COMMENT ON COLUMN farmer_data_sources.last_error_at IS 
'Timestamp of last connection error - used for circuit breaker logic to temporarily skip failing sources';
