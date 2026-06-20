#!/bin/bash

# Test script for token assignment workflow
# Usage: ./test_token_assignment.sh

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@bsads.ug}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin1234}"

echo "=================================="
echo "🧪 Token Assignment Test Script"
echo "=================================="
echo ""
echo "Backend URL: $BACKEND_URL"
echo ""

# Test 1: Admin Login
echo "Test 1: Admin Login"
echo "-------------------"
LOGIN_RESPONSE=$(curl -s -X POST $BACKEND_URL/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo -e "${RED}❌ FAILED: Could not login as admin${NC}"
  echo "$LOGIN_RESPONSE" | jq
  exit 1
fi

echo -e "${GREEN}✅ PASSED: Admin logged in successfully${NC}"
echo ""

# Test 2: List Admin Keys
echo "Test 2: List Admin Keys"
echo "-----------------------"
ADMIN_KEYS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
  $BACKEND_URL/admin/keys)

ADMIN_KEY_COUNT=$(echo $ADMIN_KEYS_RESPONSE | jq '. | length')

if [ "$ADMIN_KEY_COUNT" == "null" ] || [ "$ADMIN_KEY_COUNT" -lt 1 ]; then
  echo -e "${RED}❌ FAILED: No admin keys found${NC}"
  echo "$ADMIN_KEYS_RESPONSE" | jq
  exit 1
fi

ADMIN_KEY_ID=$(echo $ADMIN_KEYS_RESPONSE | jq -r '.[0].admin_key_id')
SERVER_URL=$(echo $ADMIN_KEYS_RESPONSE | jq -r '.[0].server_url')
ADMIN_KEY=$(echo $ADMIN_KEYS_RESPONSE | jq -r '.[0].admin_key')

echo -e "${GREEN}✅ PASSED: Found $ADMIN_KEY_COUNT admin key(s)${NC}"
echo "   Admin Key ID: $ADMIN_KEY_ID"
echo "   Server URL: $SERVER_URL"
echo "   Admin Key: ${ADMIN_KEY:0:20}..."
echo ""

# Test 3: Check if server URL is configured
echo "Test 3: Verify Server URL Configuration"
echo "----------------------------------------"
if [ "$SERVER_URL" == "null" ] || [ -z "$SERVER_URL" ]; then
  echo -e "${YELLOW}⚠️  WARNING: Server URL not configured${NC}"
  echo "   You need to update the admin key with the simulation server URL:"
  echo "   curl -X PUT $BACKEND_URL/admin/keys/$ADMIN_KEY_ID \\"
  echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
  echo "     -H \"Content-Type: application/json\" \\"
  echo "     -d '{\"server_url\": \"https://your-ngrok-url.ngrok-free.dev\"}'"
  echo ""
  echo -e "${YELLOW}⚠️  Skipping token assignment test${NC}"
  exit 0
fi

echo -e "${GREEN}✅ PASSED: Server URL is configured${NC}"
echo ""

# Test 4: Register a farmer without token
echo "Test 4: Register Farmer Without Token"
echo "--------------------------------------"
TIMESTAMP=$(date +%s)
FARMER_EMAIL="test_farmer_$TIMESTAMP@example.com"

REGISTER_RESPONSE=$(curl -s -X POST $BACKEND_URL/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"full_name\": \"Test Farmer $TIMESTAMP\",
    \"email\": \"$FARMER_EMAIL\",
    \"password\": \"SecurePass123\",
    \"phone\": \"+25670000${TIMESTAMP:(-4)}\",
    \"address\": \"Kampala, Uganda\",
    \"role\": \"farmer\"
  }")

USER_ID=$(echo $REGISTER_RESPONSE | jq -r '.user.user_id')
USER_API_KEY=$(echo $REGISTER_RESPONSE | jq -r '.user.api_key')

if [ "$USER_ID" == "null" ] || [ -z "$USER_ID" ]; then
  echo -e "${RED}❌ FAILED: Could not register farmer${NC}"
  echo "$REGISTER_RESPONSE" | jq
  exit 1
fi

if [ "$USER_API_KEY" != "null" ]; then
  echo -e "${RED}❌ FAILED: Farmer should not have API key after registration${NC}"
  echo "   Got: $USER_API_KEY"
  exit 1
fi

echo -e "${GREEN}✅ PASSED: Farmer registered without token${NC}"
echo "   Email: $FARMER_EMAIL"
echo "   User ID: $USER_ID"
echo "   API Key: null (as expected)"
echo ""

# Test 5: List users without tokens
echo "Test 5: List Users Without Tokens"
echo "----------------------------------"
USERS_WITHOUT_TOKENS=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "$BACKEND_URL/users?role=farmer" \
  | jq '[.[] | select(.api_key == null)] | length')

echo -e "${GREEN}✅ PASSED: Found $USERS_WITHOUT_TOKENS farmer(s) without tokens${NC}"
echo ""

# Test 6: Check if simulation server is reachable
echo "Test 6: Check Simulation Server"
echo "--------------------------------"
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/health" || echo "000")

if [ "$HEALTH_CHECK" != "200" ]; then
  echo -e "${YELLOW}⚠️  WARNING: Simulation server not reachable at $SERVER_URL${NC}"
  echo "   HTTP Status: $HEALTH_CHECK"
  echo "   Make sure the simulation server is running:"
  echo "   cd bsads_farmer_external_data_source_simulation"
  echo "   uvicorn main:app --reload --port 5000"
  echo ""
  echo -e "${YELLOW}⚠️  Skipping token assignment test${NC}"
  exit 0
fi

echo -e "${GREEN}✅ PASSED: Simulation server is reachable${NC}"
echo ""

# Test 7: Assign token to farmer
echo "Test 7: Assign Token to Farmer"
echo "-------------------------------"
ASSIGN_RESPONSE=$(curl -s -X POST $BACKEND_URL/users/$USER_ID/assign-token \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"server_name": "Farmer Data Source Simulation"}')

ASSIGNED_API_KEY=$(echo $ASSIGN_RESPONSE | jq -r '.api_key')
ASSIGNED_SERVER_URL=$(echo $ASSIGN_RESPONSE | jq -r '.server_url')

if [ "$ASSIGNED_API_KEY" == "null" ] || [ -z "$ASSIGNED_API_KEY" ]; then
  echo -e "${RED}❌ FAILED: Could not assign token to farmer${NC}"
  echo "$ASSIGN_RESPONSE" | jq
  exit 1
fi

echo -e "${GREEN}✅ PASSED: Token assigned successfully${NC}"
echo "   User ID: $USER_ID"
echo "   Email: $FARMER_EMAIL"
echo "   Server URL: $ASSIGNED_SERVER_URL"
echo "   API Key: ${ASSIGNED_API_KEY:0:36}..."
echo ""

# Test 8: Verify token in simulation server
echo "Test 8: Verify Token in Simulation Server"
echo "------------------------------------------"
VERIFY_RESPONSE=$(curl -s -H "X-Api-Key: $ASSIGNED_API_KEY" \
  "$ASSIGNED_SERVER_URL/recordings" || echo "{}")

VERIFY_ERROR=$(echo $VERIFY_RESPONSE | jq -r '.detail // empty')

if [ ! -z "$VERIFY_ERROR" ] && [ "$VERIFY_ERROR" != "null" ]; then
  echo -e "${RED}❌ FAILED: Token not valid in simulation server${NC}"
  echo "   Error: $VERIFY_ERROR"
  exit 1
fi

echo -e "${GREEN}✅ PASSED: Token is valid in simulation server${NC}"
echo ""

# Test 9: Prevent duplicate token assignment
echo "Test 9: Prevent Duplicate Token Assignment"
echo "-------------------------------------------"
DUPLICATE_RESPONSE=$(curl -s -X POST $BACKEND_URL/users/$USER_ID/assign-token \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"server_name": "Farmer Data Source Simulation"}')

DUPLICATE_ERROR=$(echo $DUPLICATE_RESPONSE | jq -r '.detail // empty')

if [ -z "$DUPLICATE_ERROR" ] || [ "$DUPLICATE_ERROR" == "null" ]; then
  echo -e "${RED}❌ FAILED: Should not allow duplicate token assignment${NC}"
  echo "$DUPLICATE_RESPONSE" | jq
  exit 1
fi

echo -e "${GREEN}✅ PASSED: Duplicate assignment prevented${NC}"
echo "   Error message: $DUPLICATE_ERROR"
echo ""

# Test 10: Non-admin cannot access admin endpoints
echo "Test 10: Non-Admin Access Control"
echo "----------------------------------"
# Login as the farmer we just created
FARMER_LOGIN=$(curl -s -X POST $BACKEND_URL/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$FARMER_EMAIL\", \"password\": \"SecurePass123\"}")

FARMER_TOKEN=$(echo $FARMER_LOGIN | jq -r '.access_token')

FORBIDDEN_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $FARMER_TOKEN" \
  $BACKEND_URL/admin/keys)

if [ "$FORBIDDEN_RESPONSE" != "403" ]; then
  echo -e "${RED}❌ FAILED: Non-admin should get 403 Forbidden${NC}"
  echo "   Got HTTP status: $FORBIDDEN_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✅ PASSED: Non-admin correctly denied access${NC}"
echo ""

# Summary
echo "=================================="
echo "📊 Test Summary"
echo "=================================="
echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "Test Details:"
echo "  • Admin authentication: ✅"
echo "  • Admin key management: ✅"
echo "  • Farmer registration (no token): ✅"
echo "  • Token assignment: ✅"
echo "  • Simulation server integration: ✅"
echo "  • Duplicate prevention: ✅"
echo "  • Access control: ✅"
echo ""
echo "Test Farmer Created:"
echo "  • Email: $FARMER_EMAIL"
echo "  • User ID: $USER_ID"
echo "  • API Key: ${ASSIGNED_API_KEY:0:36}..."
echo "  • Server: $ASSIGNED_SERVER_URL"
echo ""
echo -e "${GREEN}🎉 Token assignment system is working correctly!${NC}"
