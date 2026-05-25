-- Clear all data from BSADS database
-- This keeps the table structure but removes all records
-- Run with: PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -f clear_database.sql

-- Disable foreign key checks temporarily for faster deletion
SET session_replication_role = 'replica';

-- Clear all tables in reverse dependency order
TRUNCATE TABLE system_logs CASCADE;
TRUNCATE TABLE advisory_actions CASCADE;
TRUNCATE TABLE advisories CASCADE;
TRUNCATE TABLE alerts CASCADE;
TRUNCATE TABLE inference_results CASCADE;
TRUNCATE TABLE environmental_data CASCADE;
TRUNCATE TABLE audio_sources CASCADE;
TRUNCATE TABLE farmer_data_sources CASCADE;
TRUNCATE TABLE hives CASCADE;
TRUNCATE TABLE users CASCADE;
TRUNCATE TABLE advisory_templates CASCADE;

-- Re-enable foreign key checks
SET session_replication_role = 'origin';

-- Show confirmation
SELECT 'Database cleared successfully!' AS status;

-- Show table counts (should all be 0)
SELECT 
    'users' AS table_name, COUNT(*) AS count FROM users
UNION ALL
SELECT 'hives', COUNT(*) FROM hives
UNION ALL
SELECT 'farmer_data_sources', COUNT(*) FROM farmer_data_sources
UNION ALL
SELECT 'audio_sources', COUNT(*) FROM audio_sources
UNION ALL
SELECT 'inference_results', COUNT(*) FROM inference_results
UNION ALL
SELECT 'alerts', COUNT(*) FROM alerts
UNION ALL
SELECT 'advisories', COUNT(*) FROM advisories
UNION ALL
SELECT 'advisory_templates', COUNT(*) FROM advisory_templates;
