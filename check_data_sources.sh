#!/bin/bash
# Quick diagnostic script to check farmer data source configurations

echo "==================================="
echo "BSADS Data Source Health Check"
echo "==================================="
echo ""

# Load DATABASE_URL from .env if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep DATABASE_URL | xargs)
fi

DB_URL="${DATABASE_URL:-postgresql://bee_user:bee_user@localhost:5432/bee_db}"

echo "📊 Active Data Sources:"
echo "-----------------------------------"
psql "$DB_URL" -c "
SELECT 
    fds.source_id,
    h.hive_name,
    u.email as farmer_email,
    fds.connection_config->>'api_base_url' as api_url,
    CASE 
        WHEN fds.connection_config->>'api_key' IS NOT NULL THEN '✓ Configured'
        ELSE '✗ Missing'
    END as api_key,
    fds.is_active,
    fds.last_scanned_at,
    fds.last_error_at,
    CASE 
        WHEN fds.last_error_at > NOW() - INTERVAL '10 minutes' THEN '⚠️  Recent errors'
        WHEN fds.last_scanned_at IS NULL THEN '⏳ Never scanned'
        ELSE '✓ OK'
    END as status
FROM farmer_data_sources fds
JOIN hives h ON h.hive_id = fds.hive_id
JOIN users u ON u.user_id = fds.user_id
WHERE fds.is_active = true
ORDER BY fds.last_error_at DESC NULLS LAST, fds.last_scanned_at DESC NULLS LAST;
"

echo ""
echo "📈 Summary:"
echo "-----------------------------------"
psql "$DB_URL" -c "
SELECT 
    COUNT(*) as total_sources,
    COUNT(*) FILTER (WHERE is_active = true) as active,
    COUNT(*) FILTER (WHERE is_active = false) as inactive,
    COUNT(*) FILTER (WHERE last_error_at > NOW() - INTERVAL '1 hour') as recent_errors
FROM farmer_data_sources;
"

echo ""
echo "👨‍🌾 Farmers with Credentials:"
echo "-----------------------------------"
psql "$DB_URL" -c "
SELECT 
    email,
    server_url,
    CASE 
        WHEN api_key IS NOT NULL THEN '✓ Configured'
        ELSE '✗ Missing'
    END as api_key_status
FROM users
WHERE role = 'farmer' AND server_url IS NOT NULL;
"

echo ""
echo "💡 Tips:"
echo "  - If 'Recent errors' shows, the poller will auto-skip for 10 minutes"
echo "  - Check that api_url points to farmer's server (not 196.43.168.57:8086)"
echo "  - Use POST /hives/{hive_id}/data-source/configure to fix URLs"
echo ""
