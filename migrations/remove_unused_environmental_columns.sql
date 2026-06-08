-- Migration: Remove unused columns from environmental_data table
-- Date: 2026-06-08
-- Description: Remove population_k_bees and nectar_flow_kg_per_day columns as they're not being used
--              The system only tracks temperature and humidity from weather APIs

-- Remove unused columns
ALTER TABLE environmental_data 
DROP COLUMN IF EXISTS population_k_bees,
DROP COLUMN IF EXISTS nectar_flow_kg_per_day;

-- Add comments for documentation
COMMENT ON TABLE environmental_data IS 'Stores temperature and humidity data from weather APIs, recorded when audio is captured';
COMMENT ON COLUMN environmental_data.temperature IS 'Temperature in Celsius from weather API';
COMMENT ON COLUMN environmental_data.humidity IS 'Relative humidity percentage from weather API';
COMMENT ON COLUMN environmental_data.recorded_at IS 'Timestamp when the environmental data was captured (matches audio capture time)';
