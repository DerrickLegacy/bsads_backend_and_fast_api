#!/bin/bash

# Script to check if the poller is working correctly

echo "========================================="
echo "BSADS Poller Status Check"
echo "========================================="
echo ""

# Database connection
DB_USER="bee_user"
DB_PASS="bee_user"
DB_NAME="bee_db"
DB_HOST="localhost"

echo "1. Checking active data sources..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT 
    source_id,
    hive_id,
    source_type,
    source_path,
    is_active,
    last_scanned_at
FROM farmer_data_sources
WHERE is_active = true
ORDER BY last_scanned_at DESC NULLS LAST;
"

echo ""
echo "2. Checking pending audio sources..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT 
    audio_id,
    hive_id,
    source_url,
    status,
    ingestion_timestamp
FROM audio_sources
WHERE status = 'pending'
ORDER BY ingestion_timestamp DESC
LIMIT 10;
"

echo ""
echo "3. Checking recently processed audio..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT 
    audio_id,
    hive_id,
    source_url,
    status,
    ingestion_timestamp
FROM audio_sources
WHERE status IN ('processed', 'processing')
ORDER BY ingestion_timestamp DESC
LIMIT 10;
"

echo ""
echo "4. Checking recent inference results..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT 
    inference_id,
    hive_id,
    hive_state,
    confidence_score,
    created_at
FROM inference_results
ORDER BY created_at DESC
LIMIT 10;
"

echo ""
echo "========================================="
echo "Troubleshooting Tips:"
echo "========================================="
echo ""
echo "If no active data sources:"
echo "  → Create a hive with server_url and api_key"
echo "  → Or configure data source manually"
echo ""
echo "If last_scanned_at is NULL or old:"
echo "  → Check if server is running"
echo "  → Check server logs for errors"
echo "  → Verify farmer's external server is accessible"
echo ""
echo "If no pending audio sources:"
echo "  → Check if farmer has audio files on their server"
echo "  → Test: curl -H 'X-API-Key: key' https://server/recordings"
echo ""
echo "If pending but not processing:"
echo "  → Check HuggingFace API configuration"
echo "  → Check server logs for errors"
echo "  → Verify HF_SPACE_NAME in .env"
echo ""
