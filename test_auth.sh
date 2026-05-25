#!/bin/bash

# Test authentication flow with new server_url and api_key fields

API_URL="http://localhost:8000"

echo "========================================="
echo "Testing BSADS Authentication Flow"
echo "========================================="
echo ""

# Step 1: Register a new user
echo "1. Registering new user..."
REGISTER_RESPONSE=$(curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "email": "testuser_'$(date +%s)'@example.com",
    "password": "TestPass123!",
    "phone": "070'$(date +%s | tail -c 8)'",
    "address": "Kampala, Uganda",
    "role": "farmer",
    "server_url": "https://test-server.ngrok-free.dev",
    "api_key": "test-api-key-'$(date +%s)'"
  }')

echo "$REGISTER_RESPONSE" | jq '.'

# Extract token and email from registration
TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.access_token')
EMAIL=$(echo "$REGISTER_RESPONSE" | jq -r '.user.email')
SERVER_URL=$(echo "$REGISTER_RESPONSE" | jq -r '.user.server_url')
API_KEY=$(echo "$REGISTER_RESPONSE" | jq -r '.user.api_key')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Registration failed"
  exit 1
fi

echo ""
echo "✅ Registration successful!"
echo "   Email: $EMAIL"
echo "   Server URL: $SERVER_URL"
echo "   API Key: $API_KEY"
echo "   Token: ${TOKEN:0:50}..."
echo ""

# Step 2: Test /auth/me with the token
echo "2. Testing /auth/me endpoint..."
ME_RESPONSE=$(curl -s -X GET $API_URL/auth/me \
  -H "Authorization: Bearer $TOKEN")

echo "$ME_RESPONSE" | jq '.'

USER_ID=$(echo "$ME_RESPONSE" | jq -r '.user_id')

if [ "$USER_ID" = "null" ] || [ -z "$USER_ID" ]; then
  echo "❌ /auth/me failed"
  exit 1
fi

echo ""
echo "✅ /auth/me successful!"
echo ""

# Step 3: Create a hive (should auto-configure with HTTP API)
echo "3. Creating a hive (should auto-configure HTTP API data source)..."
HIVE_RESPONSE=$(curl -s -X POST $API_URL/hives \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hive_location": "Test Farm, North Field",
    "hive_name": "Test Hive 1",
    "hive_type": "Langstroth",
    "latitude": 0.3476,
    "longitude": 32.5825
  }')

echo "$HIVE_RESPONSE" | jq '.'

HIVE_ID=$(echo "$HIVE_RESPONSE" | jq -r '.hive_id')

if [ "$HIVE_ID" = "null" ] || [ -z "$HIVE_ID" ]; then
  echo "❌ Hive creation failed"
  exit 1
fi

echo ""
echo "✅ Hive created successfully!"
echo "   Hive ID: $HIVE_ID"
echo ""

# Step 4: Check data source configuration
echo "4. Checking data source configuration..."
DATASOURCE_RESPONSE=$(curl -s -X GET $API_URL/hives/$HIVE_ID/data-source \
  -H "Authorization: Bearer $TOKEN")

echo "$DATASOURCE_RESPONSE" | jq '.'

SOURCE_TYPE=$(echo "$DATASOURCE_RESPONSE" | jq -r '.source_type')
IS_ACTIVE=$(echo "$DATASOURCE_RESPONSE" | jq -r '.is_active')

echo ""
if [ "$SOURCE_TYPE" = "http_api" ]; then
  echo "✅ Data source type: $SOURCE_TYPE"
else
  echo "⚠️  Data source type: $SOURCE_TYPE (expected: http_api)"
fi

if [ "$IS_ACTIVE" = "true" ]; then
  echo "✅ Data source is active"
else
  echo "⚠️  Data source is inactive (connection test may have failed)"
fi

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "✅ User registered with server credentials"
echo "✅ Authentication working"
echo "✅ Hive created"
echo "✅ Data source configured as: $SOURCE_TYPE"
echo ""
echo "Save these for testing:"
echo "  Email: $EMAIL"
echo "  Password: TestPass123!"
echo "  Hive ID: $HIVE_ID"
echo "  Token: $TOKEN"
echo ""
