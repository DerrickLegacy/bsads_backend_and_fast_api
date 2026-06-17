#!/bin/bash
# Test the farmer's external API to see folder structure

NGROK_URL="https://jockstrap-boxlike-revisable.ngrok-free.dev"
API_KEY="fd06d12e-a374-47b1-b96c-69e1bd809b5c"

echo "==================================="
echo "Testing Farmer API"
echo "==================================="
echo ""

echo "1️⃣  Health Check:"
echo "-----------------------------------"
curl -s "$NGROK_URL/health" | jq '.' || curl -s "$NGROK_URL/health"
echo ""
echo ""

echo "2️⃣  List All Recordings:"
echo "-----------------------------------"
curl -s -H "X-API-Key: $API_KEY" "$NGROK_URL/recordings" | jq '.' || curl -s -H "X-API-Key: $API_KEY" "$NGROK_URL/recordings"
echo ""
echo ""

echo "3️⃣  List Recordings for 'strtting' hive:"
echo "-----------------------------------"
curl -s -H "X-API-Key: $API_KEY" "$NGROK_URL/recordings?hive_name=strtting" | jq '.' || curl -s -H "X-API-Key: $API_KEY" "$NGROK_URL/recordings?hive_name=strtting"
echo ""
echo ""

echo "💡 Tips:"
echo "  - If you see 'recordings': [], the folder exists but has no audio files"
echo "  - Upload .wav files to: recordings/$API_KEY/strtting/"
echo "  - The folder is on the machine running the farmer simulation server"
echo ""
