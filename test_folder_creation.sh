#!/bin/bash

# Test script for automatic hive folder creation
# This script tests the complete flow from user registration to folder creation

set -e  # Exit on error

echo "========================================="
echo "Testing Automatic Hive Folder Creation"
echo "========================================="
echo ""

# Configuration
BSADS_URL="http://localhost:8000"
FARMER_URL="http://localhost:8001"
ADMIN_KEY="e65c13554d75c38017ccdb327f263fb1d5fb1b1e33244fc6d23e60b42858fdda"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Create API key on farmer's server${NC}"
API_KEY_RESPONSE=$(curl -s -X POST "${FARMER_URL}/admin/keys" \
  -H "x-admin-key: ${ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"client_name": "test_farmer"}')

API_KEY=$(echo $API_KEY_RESPONSE | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)

if [ -z "$API_KEY" ]; then
    echo -e "${RED}✗ Failed to create API key${NC}"
    echo "Response: $API_KEY_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ API key created: ${API_KEY}${NC}"
echo ""

echo -e "${YELLOW}Step 2: Register user with server credentials${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "${BSADS_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"test_farmer_$(date +%s)\",
    \"email\": \"test$(date +%s)@example.com\",
    \"password\": \"password123\",
    \"role\": \"farmer\",
    \"server_url\": \"${FARMER_URL}\",
    \"api_key\": \"${API_KEY}\"
  }")

USERNAME=$(echo $REGISTER_RESPONSE | grep -o '"username":"[^"]*"' | cut -d'"' -f4)

if [ -z "$USERNAME" ]; then
    echo -e "${RED}✗ Failed to register user${NC}"
    echo "Response: $REGISTER_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ User registered: ${USERNAME}${NC}"
echo ""

echo -e "${YELLOW}Step 3: Login to get token${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${BSADS_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"${USERNAME}\",
    \"password\": \"password123\"
  }")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Failed to login${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Login successful${NC}"
echo ""

echo -e "${YELLOW}Step 4: Create hive with name 'Test Hive 001'${NC}"
HIVE_RESPONSE=$(curl -s -X POST "${BSADS_URL}/hives" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "hive_name": "Test Hive 001",
    "hive_location": "Kampala",
    "hive_type": "Langstroth",
    "installation_date": "2026-05-25",
    "latitude": 0.332068,
    "longitude": 32.570436
  }')

HIVE_ID=$(echo $HIVE_RESPONSE | grep -o '"hive_id":"[^"]*"' | cut -d'"' -f4)
SUGGESTED_FOLDER=$(echo $HIVE_RESPONSE | grep -o '"suggested_remote_folder":"[^"]*"' | cut -d'"' -f4)

if [ -z "$HIVE_ID" ]; then
    echo -e "${RED}✗ Failed to create hive${NC}"
    echo "Response: $HIVE_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Hive created: ${HIVE_ID}${NC}"
echo -e "${GREEN}✓ Suggested folder: ${SUGGESTED_FOLDER}${NC}"
echo ""

echo -e "${YELLOW}Step 5: Verify folder exists on farmer's server${NC}"
RECORDINGS_DIR="bsads_farmer_external_data_source_simulation/data/recordings"
FOLDER_PATH="${RECORDINGS_DIR}/${API_KEY}/Test Hive 001"

if [ -d "$FOLDER_PATH" ]; then
    echo -e "${GREEN}✓ Folder exists: ${FOLDER_PATH}${NC}"
else
    echo -e "${RED}✗ Folder not found: ${FOLDER_PATH}${NC}"
    echo "Checking what folders exist:"
    ls -la "${RECORDINGS_DIR}/${API_KEY}/" || echo "No folders found"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 6: Test listing recordings (should be empty)${NC}"
RECORDINGS_RESPONSE=$(curl -s -X GET "${FARMER_URL}/recordings?hive_id=Test%20Hive%20001" \
  -H "X-API-Key: ${API_KEY}")

echo "Response: $RECORDINGS_RESPONSE"
echo ""

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}✓ All tests passed!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Summary:"
echo "  - API Key: ${API_KEY}"
echo "  - Username: ${USERNAME}"
echo "  - Hive ID: ${HIVE_ID}"
echo "  - Folder: ${FOLDER_PATH}"
echo ""
echo "Next steps:"
echo "  1. Place audio files in: ${FOLDER_PATH}"
echo "  2. The poller will automatically detect and process them"
echo ""
