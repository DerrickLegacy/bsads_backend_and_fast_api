# User Registration Guide - HTTP API Authentication

**How to register a new farmer with their external data source credentials**

---

## Overview

The BSADS system now uses **HTTP API authentication only** (SSH is no longer supported). When registering a new farmer, you can optionally provide their external server URL and API key, which will automatically configure data sources for all their hives.

---

## Registration Flow

### Option 1: Register with Server Credentials (Recommended)

When the farmer has already set up their external data source server, register them with their credentials:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "password": "secure_password_123",
    "phone": "+1234567890",
    "address": "123 Farm Road, Rural Area",
    "role": "farmer",
    "server_url": "https://abc123-xyz789.ngrok-free.dev",
    "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "user_id": "uuid-here",
    "full_name": "John Doe",
    "email": "john@example.com",
    "role": "farmer",
    "server_url": "https://abc123-xyz789.ngrok-free.dev",
    "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "created_at": "2026-05-25T10:30:00Z"
  }
}
```

**Benefits:**
- All hives created by this farmer will automatically be configured with HTTP API data source
- Connection is tested when each hive is created
- No need to manually configure data sources for each hive

### Option 2: Register without Credentials

If the farmer hasn't set up their server yet, register them without credentials:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Jane Smith",
    "email": "jane@example.com",
    "password": "secure_password_456",
    "role": "farmer"
  }'
```

**Later, update their profile with credentials:**
```bash
curl -X PUT http://localhost:8000/auth/me \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "server_url": "https://def456-uvw123.ngrok-free.dev",
    "api_key": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

---

## Hive Creation Behavior

### With User Credentials Configured

When a farmer with `server_url` and `api_key` creates a hive:

1. **Hive is created** in the database
2. **HTTP API data source is automatically configured** using user's credentials
3. **Connection is tested** immediately
4. **Data source is activated** if connection succeeds
5. **Poller starts monitoring** the farmer's server for new audio files

**Example:**
```bash
curl -X POST http://localhost:8000/hives \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "hive_location": "North Field",
    "hive_name": "Hive 1",
    "hive_type": "Langstroth"
  }'
```

**Response includes automatic data source configuration:**
```json
{
  "hive_id": "hive-uuid",
  "owner_id": "user-uuid",
  "hive_name": "Hive 1",
  "hive_location": "North Field",
  "hive_type": "Langstroth",
  "current_state": "unknown",
  "suggested_remote_folder": "/home/farmer/recordings"
}
```

### Without User Credentials

If the farmer doesn't have credentials configured:

1. **Hive is created** in the database
2. **Inactive placeholder data source** is created
3. **Farmer must manually configure** the data source later using:
   ```bash
   POST /hives/{hive_id}/data-source/configure
   ```

---

## Manual Data Source Configuration

If you need to override the user-level credentials for a specific hive, or if the user didn't provide credentials during registration:

```bash
curl -X POST http://localhost:8000/hives/{hive_id}/data-source/configure \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "api_base_url": "https://custom-server.ngrok-free.dev",
    "api_key": "custom-api-key-for-this-hive"
  }'
```

**Response:**
```json
{
  "source_id": "source-uuid",
  "hive_id": "hive-uuid",
  "source_type": "http_api",
  "api_base_url": "https://custom-server.ngrok-free.dev",
  "connection_test": {
    "ok": true
  }
}
```

---

## Example: Complete Registration Flow

```bash
#!/bin/bash
# complete_farmer_registration.sh

BSADS_URL="http://localhost:8000"

# Step 1: Register farmer with server credentials
echo "Registering farmer..."
RESPONSE=$(curl -s -X POST $BSADS_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Alice Beekeeper",
    "email": "alice@beefarm.com",
    "password": "SecurePass123!",
    "phone": "+1234567890",
    "role": "farmer",
    "server_url": "https://abc123.ngrok-free.dev",
    "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }')

TOKEN=$(echo $RESPONSE | jq -r '.access_token')
USER_ID=$(echo $RESPONSE | jq -r '.user.user_id')

if [ "$TOKEN" = "null" ]; then
  echo "❌ Registration failed"
  echo $RESPONSE | jq '.'
  exit 1
fi
echo "✅ Farmer registered successfully"
echo "   User ID: $USER_ID"

# Step 2: Create first hive (auto-configured with HTTP API)
echo "Creating hive..."
HIVE_RESPONSE=$(curl -s -X POST $BSADS_URL/hives \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hive_location": "North Field",
    "hive_name": "Hive 1",
    "hive_type": "Langstroth",
    "latitude": 40.7128,
    "longitude": -74.0060
  }')

HIVE_ID=$(echo $HIVE_RESPONSE | jq -r '.hive_id')
echo "✅ Hive created: $HIVE_ID"

# Step 3: Verify data source is configured
echo "Checking data source..."
DATA_SOURCE=$(curl -s -H "Authorization: Bearer $TOKEN" \
  $BSADS_URL/hives/$HIVE_ID/data-source)

SOURCE_TYPE=$(echo $DATA_SOURCE | jq -r '.source_type')
IS_ACTIVE=$(echo $DATA_SOURCE | jq -r '.is_active')

echo "   Source Type: $SOURCE_TYPE"
echo "   Is Active: $IS_ACTIVE"

if [ "$SOURCE_TYPE" = "http_api" ] && [ "$IS_ACTIVE" = "true" ]; then
  echo "✅ Data source configured and active"
else
  echo "⚠️  Data source needs manual configuration"
fi

echo ""
echo "🎉 Setup complete!"
echo "The BSADS backend will now automatically poll the farmer's server."
```

---

## API Reference

### Register User
```
POST /auth/register
Content-Type: application/json

{
  "full_name": "string",
  "email": "string",
  "password": "string",
  "phone": "string (optional)",
  "address": "string (optional)",
  "role": "farmer",
  "server_url": "string (optional)",
  "api_key": "string (optional)"
}
```

### Update User Profile
```
PUT /auth/me
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "full_name": "string (optional)",
  "phone": "string (optional)",
  "address": "string (optional)",
  "server_url": "string (optional)",
  "api_key": "string (optional)"
}
```

### Create Hive
```
POST /hives
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "hive_location": "string",
  "hive_name": "string (optional)",
  "hive_type": "string (optional)",
  "latitude": number (optional),
  "longitude": number (optional)
}
```

### Configure Data Source (Manual Override)
```
POST /hives/{hive_id}/data-source/configure
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "api_base_url": "string",
  "api_key": "string"
}
```

### Get Data Source Status
```
GET /hives/{hive_id}/data-source
Authorization: Bearer <jwt-token>
```

---

## Security Best Practices

### For System Administrators:

1. **Validate credentials during registration**
   - Optionally test the connection before completing registration
   - Provide clear error messages if credentials are invalid

2. **Store API keys securely**
   - Consider encrypting API keys in the database
   - Never log API keys in plain text

3. **Rotate credentials periodically**
   - Encourage farmers to update their API keys regularly
   - Provide easy update mechanism via profile endpoint

### For Farmers:

1. **Keep API keys confidential**
   - Don't share API keys with unauthorized users
   - Revoke and regenerate if compromised

2. **Use strong passwords**
   - For both BSADS account and external server

3. **Monitor access logs**
   - Check for unusual activity on your external server

---

## Troubleshooting

### Registration succeeds but hives aren't being polled

**Check:**
1. Is the data source active?
   ```bash
   GET /hives/{hive_id}/data-source
   ```
2. Is the farmer's server running and accessible?
3. Is the ngrok tunnel active?
4. Check backend logs for connection errors

### Connection test fails during hive creation

**Possible causes:**
- Farmer's server is down
- ngrok tunnel expired
- API key is invalid
- Network connectivity issues

**Solution:**
- Hive is still created, but data source is inactive
- Fix the issue and manually configure the data source
- Or update user credentials and create a new hive

### Need to change server URL (ngrok restarted)

**Update user profile:**
```bash
curl -X PUT http://localhost:8000/auth/me \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "server_url": "https://new-url.ngrok-free.dev"
  }'
```

**Then reconfigure each hive's data source:**
```bash
curl -X POST http://localhost:8000/hives/{hive_id}/data-source/configure \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "api_base_url": "https://new-url.ngrok-free.dev",
    "api_key": "same-api-key"
  }'
```

---

## Migration from SSH

If you have existing users with SSH-configured data sources:

1. **Ask farmers to set up HTTP API servers** (see farmer documentation)
2. **Update user profiles** with new credentials
3. **Reconfigure data sources** for each hive
4. **Verify polling is working** before deactivating SSH

**Migration script example:**
```bash
# For each farmer
curl -X PUT http://localhost:8000/auth/me \
  -H "Authorization: Bearer <farmer-token>" \
  -d '{"server_url": "...", "api_key": "..."}'

# For each of their hives
curl -X POST http://localhost:8000/hives/{hive_id}/data-source/configure \
  -H "Authorization: Bearer <farmer-token>" \
  -d '{"api_base_url": "...", "api_key": "..."}'
```

---

## Need Help?

- Check the [main README](README.md) for general setup
- Review [API.md](API.md) for complete API documentation
- Check backend logs for detailed error messages
- Contact farmers if their servers are unreachable

---

**You're all set!** New farmers can now be registered with their server credentials, and hives will automatically be configured for audio polling.
