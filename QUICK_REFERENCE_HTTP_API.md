# Quick Reference - HTTP API Authentication

**One-page guide for the new authentication system**

---

## Registration

### With Server Credentials (Recommended)

```bash
POST /auth/register
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "role": "farmer",
  "server_url": "https://abc123.ngrok-free.dev",
  "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

✅ **Result:** All hives auto-configure with HTTP API data source

### Without Credentials

```bash
POST /auth/register
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "role": "farmer"
}
```

⚠️ **Result:** Must configure credentials later

---

## Update Profile

```bash
PUT /auth/me
Authorization: Bearer <token>
{
  "server_url": "https://new-url.ngrok-free.dev",
  "api_key": "new-api-key"
}
```

---

## Create Hive

```bash
POST /hives
Authorization: Bearer <token>
{
  "hive_location": "North Field",
  "hive_name": "Hive 1",
  "hive_type": "Langstroth"
}
```

**Behavior:**
- If user has credentials → Auto-configures HTTP API data source
- If user lacks credentials → Creates inactive placeholder

---

## Configure Data Source (Manual)

```bash
POST /hives/{hive_id}/data-source/configure
Authorization: Bearer <token>
{
  "api_base_url": "https://server.ngrok-free.dev",
  "api_key": "api-key-here"
}
```

**Use when:**
- User didn't provide credentials at registration
- Need to override user-level credentials for specific hive
- ngrok URL changed

---

## Check Data Source Status

```bash
GET /hives/{hive_id}/data-source
Authorization: Bearer <token>
```

**Response:**
```json
{
  "source_id": "uuid",
  "hive_id": "uuid",
  "source_type": "http_api",
  "source_path": "https://server.ngrok-free.dev",
  "is_active": true,
  "last_scanned_at": "2026-05-25T10:30:00Z"
}
```

---

## Test Farmer's Server

```bash
# Health check (no auth)
curl https://farmer-server.ngrok-free.dev/health

# List recordings (requires API key)
curl -H "X-API-Key: api-key-here" \
  https://farmer-server.ngrok-free.dev/recordings

# Download recording
curl -H "X-API-Key: api-key-here" \
  https://farmer-server.ngrok-free.dev/recordings/hive1.wav \
  --output hive1.wav
```

---

## Common Workflows

### New Farmer Setup

```bash
# 1. Register with credentials
curl -X POST $API/auth/register -d '{...}'

# 2. Create hive (auto-configured)
curl -X POST $API/hives -H "Authorization: Bearer $TOKEN" -d '{...}'

# 3. Verify data source
curl -H "Authorization: Bearer $TOKEN" $API/hives/$HIVE_ID/data-source
```

### Update ngrok URL

```bash
# 1. Update user profile
curl -X PUT $API/auth/me -H "Authorization: Bearer $TOKEN" \
  -d '{"server_url": "https://new-url.ngrok-free.dev"}'

# 2. Reconfigure each hive
curl -X POST $API/hives/$HIVE_ID/data-source/configure \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"api_base_url": "https://new-url.ngrok-free.dev", "api_key": "..."}'
```

### Migrate from SSH

```bash
# 1. Update user with HTTP API credentials
curl -X PUT $API/auth/me -H "Authorization: Bearer $TOKEN" \
  -d '{"server_url": "...", "api_key": "..."}'

# 2. Reconfigure all hives
for hive in $(curl -H "Authorization: Bearer $TOKEN" $API/hives | jq -r '.[].hive_id'); do
  curl -X POST $API/hives/$hive/data-source/configure \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"api_base_url": "...", "api_key": "..."}'
done
```

---

## Troubleshooting

### Data source inactive after hive creation

**Check:**
```bash
curl -H "Authorization: Bearer $TOKEN" $API/hives/$HIVE_ID/data-source
```

**Possible causes:**
- User doesn't have credentials configured
- Farmer's server is down
- Connection test failed

**Fix:**
```bash
# Configure manually
curl -X POST $API/hives/$HIVE_ID/data-source/configure \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"api_base_url": "...", "api_key": "..."}'
```

### Connection test fails

**Test farmer's server directly:**
```bash
curl https://farmer-server.ngrok-free.dev/health
curl -H "X-API-Key: key" https://farmer-server.ngrok-free.dev/recordings
```

**Common issues:**
- Server not running
- ngrok tunnel expired
- Invalid API key
- Firewall blocking connection

### No files being polled

**Check:**
1. Data source is active: `GET /hives/{id}/data-source`
2. Files exist on farmer's server: `GET /recordings` with API key
3. Backend logs for errors
4. `last_scanned_at` timestamp is updating

---

## Key Differences from SSH

| Feature | SSH (Old) | HTTP API (New) |
|---------|-----------|----------------|
| **Authentication** | SSH keys/passwords | API keys |
| **Configuration** | Per-hive only | User-level + per-hive override |
| **Auto-setup** | No | Yes (if user has credentials) |
| **Connection test** | Manual | Automatic on hive creation |
| **Error handling** | SSH errors | HTTP status codes |
| **Debugging** | SSH logs | HTTP logs |
| **Security** | SSH key management | API key rotation |

---

## Environment Variables

**Farmer's server `.env`:**
```bash
API_KEY=f47ac10b-58cc-4372-a567-0e02b2c3d479
RECORDINGS_DIR=/home/farmer/recordings
PORT=5000
```

**BSADS backend `.env`:**
```bash
DATABASE_URL=postgresql://user:pass@localhost/bsads_db
SECRET_KEY=your-jwt-secret
HF_API_TOKEN=your-huggingface-token
```

---

## API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/auth/register` | Register user (with optional credentials) |
| POST | `/auth/login` | Login and get JWT token |
| GET | `/auth/me` | Get current user profile |
| PUT | `/auth/me` | Update profile (including credentials) |
| POST | `/hives` | Create hive (auto-configures if credentials exist) |
| GET | `/hives/{id}/data-source` | Get data source status |
| POST | `/hives/{id}/data-source/configure` | Configure/update data source |

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (invalid data) |
| 401 | Unauthorized (invalid token/credentials) |
| 404 | Not found |
| 500 | Server error |

---

## Need More Info?

- **Full guide:** `USER_REGISTRATION_GUIDE.md`
- **Farmer setup:** `1.FARMER_API_KEY_SETUP.md`
- **Migration:** `MIGRATION_TO_HTTP_API_ONLY.md`
- **API docs:** `API.md`
- **Interactive docs:** `http://localhost:8000/docs`
