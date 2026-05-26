#!/bin/bash

echo "============================================================"
echo "POLLER MONITORING - Press Ctrl+C to stop"
echo "============================================================"
echo ""

while true; do
    clear
    echo "============================================================"
    echo "POLLER STATUS - $(date)"
    echo "============================================================"
    echo ""
    
    echo "Active Data Sources:"
    PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -c \
        "SELECT ds.hive_id, h.hive_name, u.email, ds.last_scanned_at 
         FROM farmer_data_sources ds 
         JOIN hives h ON ds.hive_id = h.hive_id 
         JOIN users u ON h.owner_id = u.user_id 
         WHERE ds.is_active = true;" 2>/dev/null
    
    echo ""
    echo "Audio Source Status:"
    PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -c \
        "SELECT status, COUNT(*) as count 
         FROM audio_sources 
         GROUP BY status;" 2>/dev/null
    
    echo ""
    echo "Recent Audio Sources (last 5):"
    PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -c \
        "SELECT audio_id, hive_id, status, ingestion_timestamp 
         FROM audio_sources 
         ORDER BY ingestion_timestamp DESC 
         LIMIT 5;" 2>/dev/null
    
    echo ""
    echo "Recent Inference Results (last 3):"
    PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -c \
        "SELECT inference_id, hive_id, hive_state, confidence_score, analyzed_at 
         FROM inference_results 
         ORDER BY analyzed_at DESC 
         LIMIT 3;" 2>/dev/null
    
    echo ""
    echo "Recent System Logs (last 5):"
    PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -c \
        "SELECT level, event_type, message, created_at 
         FROM system_logs 
         WHERE event_type IN ('poller', 'http_api', 'inference') 
         ORDER BY created_at DESC 
         LIMIT 5;" 2>/dev/null
    
    echo ""
    echo "============================================================"
    echo "Refreshing in 10 seconds... (Ctrl+C to stop)"
    echo "============================================================"
    
    sleep 10
done
