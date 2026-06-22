-- Migration: Add hive_conditions table for device sensor readings
-- Created: 2024-06-20
-- Description: Creates table for storing three-zone temperature and humidity readings from IoT devices

-- Create hive_conditions table
CREATE TABLE IF NOT EXISTS hive_conditions (
    condition_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hive_id UUID NOT NULL REFERENCES hives(hive_id) ON DELETE CASCADE,
    audio_id UUID REFERENCES audio_sources(audio_id) ON DELETE SET NULL,
    
    -- Three-zone temperature readings (Celsius)
    temp_honey NUMERIC(5, 2),
    temp_brood NUMERIC(5, 2),
    temp_exterior NUMERIC(5, 2),
    
    -- Three-zone humidity readings (percentage)
    humidity_honey NUMERIC(5, 2),
    humidity_brood NUMERIC(5, 2),
    humidity_exterior NUMERIC(5, 2),
    
    recorded_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_hive_conditions_hive_id ON hive_conditions(hive_id);
CREATE INDEX IF NOT EXISTS idx_hive_conditions_audio_id ON hive_conditions(audio_id);
CREATE INDEX IF NOT EXISTS idx_hive_conditions_recorded_at ON hive_conditions(recorded_at);

-- Add comments
COMMENT ON TABLE hive_conditions IS 'Internal hive sensor readings from IoT devices - three zones (honey, brood, exterior)';
COMMENT ON COLUMN hive_conditions.temp_honey IS 'Temperature in honey storage zone (Celsius)';
COMMENT ON COLUMN hive_conditions.temp_brood IS 'Temperature in brood rearing zone (Celsius)';
COMMENT ON COLUMN hive_conditions.temp_exterior IS 'Temperature at hive exterior/entrance (Celsius)';
COMMENT ON COLUMN hive_conditions.humidity_honey IS 'Humidity in honey storage zone (percentage)';
COMMENT ON COLUMN hive_conditions.humidity_brood IS 'Humidity in brood rearing zone (percentage)';
COMMENT ON COLUMN hive_conditions.humidity_exterior IS 'Humidity at hive exterior/entrance (percentage)';
COMMENT ON COLUMN hive_conditions.recorded_at IS 'Timestamp from device when reading was taken';
COMMENT ON COLUMN hive_conditions.audio_id IS 'Optional link to audio file recorded at same time';
