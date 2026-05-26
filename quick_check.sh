#!/bin/bash

echo "🔍 Quick Poller Status Check"
echo "=============================="
echo ""

# Check if API server is running
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ API Server is running"
else
    echo "❌ API Server is NOT running"
    echo "   Start with: uvicorn api.main:app --reload --port 8001"
fi

# Check if farmer's server is accessible
if curl -s https://jockstrap-boxlike-revisable.ngrok-free.dev/health > /dev/null 2>&1; then
    echo "✅ Farmer's server is accessible"
else
    echo "❌ Farmer's server is NOT accessible"
fi

# Check active data sources
ACTIVE_COUNT=$(PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -t -c "SELECT COUNT(*) FROM farmer_data_sources WHERE is_active = true;" 2>/dev/null | tr -d ' ')
echo "📊 Active data sources: $ACTIVE_COUNT"

# Check for recordings on farmer's server
RECORDINGS=$(curl -s -H "X-API-Key: d3c07d19-cd0d-42b5-88e2-759349a4d023" "https://jockstrap-boxlike-revisable.ngrok-free.dev/recordings?hive_id=b33556d2-7f30-4aac-ae38-9076925df80b" 2>/dev/null)
RECORDING_COUNT=$(echo "$RECORDINGS" | grep -o '"recordings":\[' | wc -l)

if [ "$RECORDING_COUNT" -gt 0 ]; then
    FILE_COUNT=$(echo "$RECORDINGS" | grep -o '\.wav' | wc -l)
    echo "📁 Files on farmer's server: $FILE_COUNT"
else
    echo "📁 Files on farmer's server: 0"
    echo "   ⚠️  Add files to: recordings/d3c07d19-cd0d-42b5-88e2-759349a4d023/b33556d2-7f30-4aac-ae38-9076925df80b/"
fi

# Check pending audio sources
PENDING_COUNT=$(PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -t -c "SELECT COUNT(*) FROM audio_sources WHERE status = 'pending';" 2>/dev/null | tr -d ' ')
echo "⏳ Pending audio sources: $PENDING_COUNT"

# Check processed audio sources
PROCESSED_COUNT=$(PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -t -c "SELECT COUNT(*) FROM audio_sources WHERE status = 'processed';" 2>/dev/null | tr -d ' ')
echo "✅ Processed audio sources: $PROCESSED_COUNT"

# Check inference results
INFERENCE_COUNT=$(PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -t -c "SELECT COUNT(*) FROM inference_results;" 2>/dev/null | tr -d ' ')
echo "🧠 Inference results: $INFERENCE_COUNT"

# Check recent errors
ERROR_COUNT=$(PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -t -c "SELECT COUNT(*) FROM system_logs WHERE level = 'error' AND created_at > NOW() - INTERVAL '5 minutes';" 2>/dev/null | tr -d ' ')
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  Recent errors (last 5 min): $ERROR_COUNT"
    echo "   Check logs with: PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -c \"SELECT * FROM system_logs WHERE level = 'error' ORDER BY created_at DESC LIMIT 5;\""
else
    echo "✅ No recent errors"
fi

echo ""
echo "=============================="
echo "For detailed testing: ./venv/bin/python test_poller_flow.py"
echo "For monitoring: ./monitor_poller.sh"
echo "For help: cat POLLER_FIX_GUIDE.md"
