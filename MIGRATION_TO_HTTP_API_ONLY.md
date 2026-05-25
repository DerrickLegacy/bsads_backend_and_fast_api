# Migration to HTTP API Only Authentication

**Date:** 2026-05-25  
**Status:** Complete  
**Breaking Change:** Yes - SSH authentication is no longer supported

---

## Summary

The BSADS backend has been updated to use **HTTP API authentication only**. SSH/SFTP authentication is no longer supported. Farmers now provide their external server URL and API key at registration, which automatically configures data sources for all their hives.

---

## What Changed

### 1. User Model Updates

**Added fields to `users` table:**
- `server_url` (VARCHAR 255) - Farmer's external server URL (e.g., `https://abc123.ngrok-free.dev`)
- `api_key` (VARCHAR 255) - API key for accessing the farmer's server

**Migration file:** `migrations/add_user_server_credentials.sql`

### 2. Registration Flow

**Before:**
```json
POST /auth/register
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "password123",
  "role": "farmer"
}
```

**After:**
```json
POST /auth/register
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "password123",
  "role": "farmer",
  "server_url": "https://abc123.ngrok-free.dev",
  "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

### 3. Hive Creation Behavior

**Before:**
- Created inactive SSH data source placeholder
- Farmer had to manually configure SSH credentials via `POST /hives/{id}/data-source/configure`

**After:**
- If user has `server_url` and `api_key`: automatically creates and tests HTTP API data source
- If user doesn't have credentials: creates inactive placeholder
- Connection is tested immediately; data source only activated if test succeeds

### 4. API Endpoints

**Removed:**
- `POST /hives/{hive_id}/data-source/configure` (SSH configuration)

**Changed:**
- `POST /hives/{hive_id}/data-source/configure-http-api` → `POST /hives/{hive_id}/data-source/configure`
  - Now the primary/only configuration endpoint
  - Still supports manual override of user-level credentials

**Updated:**
- `PUT /auth/me` - Now accepts `server_url` and `api_key` fields
- `GET /auth/me` - Returns `server_url` and `api_key` (if set)

### 5. Schema Updates

**Updated Pydantic models:**
- `UserRegister` - Added optional `server_url` and `api_key`
- `UserResponse` - Added optional `server_url` and `api_key`
- `ProfileUpdate` - Added optional `server_url` and `api_key`
- `AdminUserCreate` - Added optional `server_url` and `api_key`
- `AdminUserUpdate` - Added optional `server_url` and `api_key`
- `UserDetailResponse` - Added optional `server_url` and `api_key`

### 6. Documentation Updates

**New files:**
- `USER_REGISTRATION_GUIDE.md` - Complete guide for registering users with HTTP API credentials
- `MIGRATION_TO_HTTP_API_ONLY.md` - This file

**Updated files:**
- `1.FARMER_API_KEY_SETUP.md` - Now farmer-focused guide for connecting their server

---

## Migration Steps

### For New Installations

No migration needed. Just use the new registration flow with `server_url` and `api_key`.

### For Existing Installations

#### Step 1: Run Database Migration

```bash
# Connect to your PostgreSQL database
psql -U your_user -d bsads_db -f migrations/add_user_server_credentials.sql
```

Or if using Docker:
```bash
docker exec -i bsads_postgres psql -U postgres -d bsads_db < migrations/add_user_server_credentials.sql
```

#### Step 2: Update Existing Users

For each farmer with SSH-configured hives:

1. **Ask them to set up HTTP API server** (see farmer documentation)
2. **Get their server URL and API key**
3. **Update their user profile:**

```bash
curl -X PUT https://your-bsads-api.com/auth/me \
  -H "Authorization: Bearer <farmer-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "server_url": "https://abc123.ngrok-free.dev",
    "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }'
```

4. **Reconfigure each hive's data source:**

```bash
curl -X POST https://your-bsads-api.com/hives/{hive_id}/data-source/configure \
  -H "Authorization: Bearer <farmer-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "api_base_url": "https://abc123.ngrok-free.dev",
    "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }'
```

5. **Verify polling is working:**

```bash
curl -H "Authorization: Bearer <farmer-jwt-token>" \
  https://your-bsads-api.com/hives/{hive_id}/data-source
```

Check that `source_type` is `"http_api"` and `is_active` is `true`.

#### Step 3: Optional - Clean Up SSH Code

If you want to completely remove SSH support:

1. Delete `api/ssh_connector.py`
2. Remove SSH-related code from `api/poller.py`
3. Remove `paramiko` from `requirements.txt`
4. Update any remaining documentation references

**Note:** The current implementation keeps SSH code for backward compatibility during migration, but it's no longer used.

---

## Testing

### Test New User Registration

```bash
# Register with credentials
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test Farmer",
    "email": "test@example.com",
    "password": "TestPass123!",
    "role": "farmer",
    "server_url": "https://test.ngrok-free.dev",
    "api_key": "test-api-key-123"
  }'

# Verify credentials are stored
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123!"}'

# Use the token to check profile
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/auth/me
```

### Test Automatic Hive Configuration

```bash
# Create hive (should auto-configure if user has credentials)
curl -X POST http://localhost:8000/hives \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "hive_location": "Test Field",
    "hive_name": "Test Hive"
  }'

# Check data source was created
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/hives/{hive_id}/data-source
```

### Test Profile Update

```bash
# Update credentials
curl -X PUT http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "server_url": "https://new-url.ngrok-free.dev",
    "api_key": "new-api-key-456"
  }'

# Verify update
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/auth/me
```

---

## API Examples

### Example 1: Complete New User Flow

```bash
#!/bin/bash

# 1. Register with credentials
RESPONSE=$(curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Alice Beekeeper",
    "email": "alice@beefarm.com",
    "password": "SecurePass123!",
    "role": "farmer",
    "server_url": "https://abc123.ngrok-free.dev",
    "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }')

TOKEN=$(echo $RESPONSE | jq -r '.access_token')

# 2. Create hive (auto-configured)
HIVE=$(curl -s -X POST http://localhost:8000/hives \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hive_location": "North Field",
    "hive_name": "Hive 1"
  }')

HIVE_ID=$(echo $HIVE | jq -r '.hive_id')

# 3. Verify data source
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/hives/$HIVE_ID/data-source
```

### Example 2: Update Existing User

```bash
#!/bin/bash

# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "existing@example.com", "password": "password"}' \
  | jq -r '.access_token')

# 2. Update profile with credentials
curl -X PUT http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server_url": "https://xyz789.ngrok-free.dev",
    "api_key": "new-api-key-here"
  }'

# 3. Reconfigure existing hives
for HIVE_ID in $(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/hives | jq -r '.[].hive_id'); do
  
  curl -X POST http://localhost:8000/hives/$HIVE_ID/data-source/configure \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "api_base_url": "https://xyz789.ngrok-free.dev",
      "api_key": "new-api-key-here"
    }'
done
```

---

## Breaking Changes

### API Changes

1. **Removed endpoint:** `POST /hives/{hive_id}/data-source/configure` (SSH version)
   - **Migration:** Use `POST /hives/{hive_id}/data-source/configure` (now HTTP API only)

2. **Changed endpoint:** `POST /hives/{hive_id}/data-source/configure-http-api`
   - **Migration:** Renamed to `POST /hives/{hive_id}/data-source/configure`

3. **Schema changes:** `DataSourceConfigureSSH` removed
   - **Migration:** Use `DataSourceConfigureHTTPAPI` instead

### Database Changes

1. **New columns in `users` table:**
   - `server_url` (nullable)
   - `api_key` (nullable)

2. **Existing data sources:**
   - SSH-configured sources will continue to work during migration
   - Recommend migrating to HTTP API as soon as possible

### Code Changes

1. **SSH connector still exists** but is deprecated
   - Will be removed in future version
   - Update your code to use HTTP API

2. **Poller still supports SSH** for backward compatibility
   - Will be removed in future version

---

## Rollback Plan

If you need to rollback:

### Step 1: Revert Database Changes

```sql
ALTER TABLE users DROP COLUMN IF EXISTS server_url;
ALTER TABLE users DROP COLUMN IF EXISTS api_key;
```

### Step 2: Revert Code Changes

```bash
git revert <commit-hash>
```

### Step 3: Restart Services

```bash
docker compose restart api
```

---

## Benefits of This Change

1. **Simpler setup** - No SSH key management
2. **Better security** - API keys are easier to rotate than SSH keys
3. **Automatic configuration** - Hives auto-configure when created
4. **Consistent authentication** - One method for all farmers
5. **Better error handling** - HTTP status codes vs SSH errors
6. **Easier debugging** - HTTP logs vs SSH connection issues

---

## Support

### For Developers

- Check `USER_REGISTRATION_GUIDE.md` for implementation details
- Review `api/routers/hives.py` for hive creation logic
- See `api/http_connector.py` for HTTP API implementation

### For Farmers

- Check `1.FARMER_API_KEY_SETUP.md` for setup instructions
- Contact your BSADS administrator for help with migration

### For Administrators

- Run the database migration first
- Update existing users gradually
- Monitor logs for connection issues
- Keep SSH support enabled during migration period

---

## Timeline

- **2026-05-25:** HTTP API only implementation complete
- **2026-06-01:** Recommended migration deadline for existing users
- **2026-07-01:** SSH support will be completely removed

---

## Questions?

Contact the development team or check the documentation:
- `USER_REGISTRATION_GUIDE.md` - Registration and configuration
- `1.FARMER_API_KEY_SETUP.md` - Farmer setup guide
- `API.md` - Complete API reference
- `README.md` - General system overview
