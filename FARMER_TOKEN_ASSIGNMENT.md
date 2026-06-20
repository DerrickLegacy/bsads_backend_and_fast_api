# Farmer Token Assignment Workflow

## Overview

This document describes the new workflow where farmers can register without API credentials, and admins assign them tokens later through the admin dashboard.

## New Workflow

### Before (Old Flow)
1. Admin manually copies ADMIN_KEY from simulation server
2. Admin calls simulation server to generate farmer token
3. Admin gives farmer the token
4. **Farmer registers with token** ← Required token upfront

### After (New Flow)
1. **Farmer registers without token** ← Can register immediately!
2. Admin sees new user in dashboard
3. Admin clicks "Assign Token" button
4. System automatically:
   - Gets ADMIN_KEY from database
   - Calls simulation server with farmer's name
   - Receives generated API token
   - Updates farmer's record with token and server URL
5. Farmer can now start using the system

## Database Changes

### Users Table
- `server_url` → Now **nullable** (was required)
- `api_key` → Now **nullable** (was required)

This allows farmers to register without these credentials.

## API Endpoints

### 1. Farmer Registration (Updated)

**Endpoint:** `POST /auth/register`

**New Behavior:** `server_url` and `api_key` are now optional

```bash
# Farmers can register WITHOUT server_url and api_key
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123",
    "phone": "+256700000000",
    "address": "Kampala, Uganda",
    "role": "farmer"
  }'
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "user_id": "abc-123...",
    "full_name": "John Doe",
    "email": "john@example.com",
    "role": "farmer",
    "server_url": null,
    "api_key": null,
    "created_at": "2024-01-01T00:00:00"
  }
}
```

### 2. Admin Assigns Token (New)

**Endpoint:** `POST /users/{user_id}/assign-token`

**Authentication:** Admin only

**Request Body:**
```json
{
  "server_name": "Farmer Data Source Simulation"
}
```

**What It Does:**
1. Gets the user from database
2. Checks if user already has a token (prevents duplicates)
3. Fetches admin key for the specified server
4. Calls simulation server `/admin/keys` endpoint
5. Stores generated API key in simulation server's `api_keys.json`
6. Updates user's `server_url` and `api_key` fields
7. Returns updated user info

**Example:**
```bash
curl -X POST http://localhost:8000/users/abc-123.../assign-token \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "Farmer Data Source Simulation"
  }'
```

**Response:**
```json
{
  "user_id": "abc-123...",
  "full_name": "John Doe",
  "email": "john@example.com",
  "server_url": "https://jockstrap-boxlike-revisable.ngrok-free.dev",
  "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "assigned_at": "2024-01-01T12:00:00"
}
```

### 3. List Users Without Tokens

**Endpoint:** `GET /users?role=farmer`

Admins can filter for farmers and check which ones don't have tokens yet:

```bash
curl -H "Authorization: Bearer <admin_token>" \
  "http://localhost:8000/users?role=farmer"
```

Users with `"api_key": null` need token assignment.

## Complete Admin Workflow

### Step 1: Setup Admin Key (One-time)

```bash
# 1. Login as admin
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@bsads.ug", "password": "Admin1234"}'

# Save the access_token

# 2. Get admin keys
curl -H "Authorization: Bearer <admin_token>" \
  http://localhost:8000/admin/keys

# 3. Update server URL if needed (e.g., after ngrok restart)
curl -X PUT http://localhost:8000/admin/keys/<admin_key_id> \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "server_url": "https://your-ngrok-url.ngrok-free.dev"
  }'
```

### Step 2: Assign Tokens to Farmers

```bash
# 1. List all farmers
curl -H "Authorization: Bearer <admin_token>" \
  "http://localhost:8000/users?role=farmer"

# 2. Find users with null api_key

# 3. Assign token to each user
curl -X POST http://localhost:8000/users/<user_id>/assign-token \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"server_name": "Farmer Data Source Simulation"}'
```

## Error Handling

### User Already Has Token
```json
{
  "detail": "User already has an API key assigned. Current server: https://example.com"
}
```

### Admin Key Not Found
```json
{
  "detail": "No active admin key found for server: Farmer Data Source Simulation"
}
```

### Server URL Not Configured
```json
{
  "detail": "Server URL not configured for Farmer Data Source Simulation. Please update it in /admin/keys"
}
```

### Simulation Server Down
```json
{
  "detail": "Timeout connecting to simulation server. Please check if the server is running."
}
```

### Invalid Admin Key
```json
{
  "detail": "Invalid admin key. Please check the admin key configuration."
}
```

## Migration Steps

### For Existing Databases

1. **Run migration to make fields nullable:**
   ```bash
   python -m api.run_migration
   ```

2. **Existing users with tokens:** No action needed, they continue to work

3. **New users:** Can register without tokens, admins assign later

### For Fresh Installations

No special steps needed - the schema is already correct.

## Admin Dashboard Integration

### Required UI Components

1. **Users List View:**
   - Show all users with farmer role
   - Indicate which users have tokens (✓) and which don't (⚠)
   - "Assign Token" button for users without tokens

2. **Token Assignment Modal:**
   - User info (name, email)
   - Server selection dropdown (default: "Farmer Data Source Simulation")
   - "Assign Token" button
   - Loading state while calling API
   - Success/error messages

3. **Admin Keys Management:**
   - List all admin keys
   - Update server URLs (important after ngrok restarts)
   - Add new keys for multiple environments

### Sample UI Flow

```
┌─────────────────────────────────────┐
│ Users List                          │
├─────────────────────────────────────┤
│ John Doe                            │
│ john@example.com                    │
│ Token: ⚠ Not Assigned               │
│ [Assign Token]                      │
├─────────────────────────────────────┤
│ Jane Smith                          │
│ jane@example.com                    │
│ Token: ✓ Assigned                   │
│ Server: https://abc.ngrok-free.dev  │
└─────────────────────────────────────┘

Click [Assign Token]:
┌─────────────────────────────────────┐
│ Assign Token to John Doe            │
├─────────────────────────────────────┤
│ Email: john@example.com             │
│                                     │
│ Server: [Farmer Data Source ▼]     │
│                                     │
│        [Cancel]  [Assign Token]     │
└─────────────────────────────────────┘

After Assignment:
┌─────────────────────────────────────┐
│ ✓ Token Assigned Successfully       │
├─────────────────────────────────────┤
│ User: John Doe                      │
│ Server: https://abc.ngrok-free.dev  │
│ API Key: f47ac10b-58cc...           │
└─────────────────────────────────────┘
```

## Security Considerations

1. **Only Admins Can Assign Tokens:** The endpoint requires admin role
2. **Prevent Duplicate Assignment:** Cannot assign token if user already has one
3. **Validate Admin Key:** System checks if admin key exists and is active
4. **Error Handling:** Proper error messages for all failure scenarios
5. **Audit Trail:** Updates are timestamped in `updated_at` field

## Benefits of New Flow

✅ **Simplified Onboarding:** Farmers can register immediately without waiting for admin  
✅ **Centralized Management:** All token assignment happens in one place  
✅ **Automated Process:** No manual copying of keys or URLs  
✅ **Error Prevention:** System validates everything before assignment  
✅ **Better UX:** Admins can see at a glance which users need tokens  
✅ **Audit Trail:** Track when tokens were assigned  

## Testing Checklist

- [ ] Farmer can register without `server_url` and `api_key`
- [ ] Farmer registration validates optional fields correctly
- [ ] Admin can list users and see which have tokens
- [ ] Admin can assign token to user without token
- [ ] System prevents duplicate token assignment
- [ ] Generated token is stored in simulation server's `api_keys.json`
- [ ] User record is updated with correct `server_url` and `api_key`
- [ ] Error handling works for all failure scenarios
- [ ] Non-admin users cannot access assignment endpoint
- [ ] Existing users with tokens continue to work normally

## Backward Compatibility

✅ **Old registration flow still works:** Farmers can still register with `server_url` and `api_key` if they already have them

✅ **Existing users unaffected:** All current users with tokens continue working normally

✅ **Both flows coexist:** The system supports both workflows simultaneously
