-- View all currently configured data sources
-- Run this first to see what's in your database

SELECT 
    fds.source_id,
    fds.hive_id,
    h.hive_name,
    u.email as farmer_email,
    fds.source_type,
    fds.source_path,
    fds.connection_config->>'api_base_url' as api_url,
    fds.is_active,
    fds.last_scanned_at,
    fds.last_error_at
FROM farmer_data_sources fds
JOIN hives h ON h.hive_id = fds.hive_id
JOIN users u ON u.user_id = fds.user_id
WHERE fds.is_active = true
ORDER BY fds.last_scanned_at DESC NULLS LAST;

-- Temporarily deactivate misconfigured sources pointing to wrong host
-- (Uncomment to run after reviewing the above query)

-- UPDATE farmer_data_sources
-- SET is_active = false
-- WHERE connection_config->>'api_base_url' LIKE '%196.43.168.57:8086%';

-- Check if any farmers have their server_url configured correctly
SELECT 
    user_id,
    email,
    full_name,
    role,
    server_url,
    CASE 
        WHEN api_key IS NOT NULL THEN '***configured***'
        ELSE NULL
    END as api_key_status
FROM users
WHERE role = 'farmer' AND server_url IS NOT NULL;
