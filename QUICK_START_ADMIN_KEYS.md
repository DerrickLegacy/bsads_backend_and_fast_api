# Quick Start: Admin Key Management

## 🚀 Setup (One-time)

### Option 1: Fresh Installation (Recommended)

If starting from scratch or using `RESET_DATABASE=true`:

1. **Start the server** - The admin key will be automatically seeded:
   ```bash
   cd bsads_backend_and_fast_api
   uvicorn api.main:app --reload --port 8000
   ```

2. **Verify seeding** - Look for this message in the logs:
   ```
   ✓ Seeded simulation admin key  →  128d3e857c80d2313420...
   ```

### Option 2: Existing Database

If you have an existing database:

1. **Run the migration** to create the `admin_keys` table:
   ```bash
   cd bsads_backend_and_fast_api
   python -m api.run_migration
   ```

2. **Seed the admin key** from the simulation server:
   ```bash
   python -m api.migrate_admin_key
   ```

3. **Start the server**:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

## 📋 Usage Examples

### 1. Login as Admin

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@bsads.ug",
    "password": "Admin1234"
  }'
```

**Save the access_token from the response!**

### 2. List All Admin Keys

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/admin/keys
```

**Response:**
```json
[
  {
    "admin_key_id": "abc-123...",
    "server_name": "Farmer Data Source Simulation",
    "server_url": null,
    "admin_key": "128d3e857c80d23134206cbd707300050abc64966a1b5be9c107f8bd7d5b56eb",
    "description": "Default admin key for farmer external data source simulation server",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

### 3. Get Key by Server Name

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "http://localhost:8000/admin/keys/server/Farmer%20Data%20Source%20Simulation"
```

### 4. Generate Farmer API Token

Now use the admin key to generate a token for a farmer:

```bash
# Replace YOUR_NGROK_URL with your actual simulation server URL
curl -X POST https://YOUR_NGROK_URL/admin/keys \
  -H "X-Admin-Key: 128d3e857c80d23134206cbd707300050abc64966a1b5be9c107f8bd7d5b56eb" \
  -H "Content-Type: application/json" \
  -d '{"client_name": "John Doe"}'
```

**Response:**
```json
{
  "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "client_name": "John Doe"
}
```

### 5. Farmer Registration

Give the API key to the farmer for registration:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123",
    "phone": "+256700000000",
    "address": "Kampala, Uganda",
    "role": "farmer",
    "server_url": "https://YOUR_NGROK_URL",
    "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }'
```

## 🔧 Management Operations

### Add a New Admin Key

```bash
curl -X POST http://localhost:8000/admin/keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "Production Server",
    "server_url": "https://prod.example.com",
    "admin_key": "your-production-key-here",
    "description": "Production environment admin key",
    "is_active": true
  }'
```

### Update Server URL

```bash
curl -X PUT http://localhost:8000/admin/keys/ADMIN_KEY_ID \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server_url": "https://new-ngrok-url.app"
  }'
```

### Deactivate a Key

```bash
curl -X PUT http://localhost:8000/admin/keys/ADMIN_KEY_ID \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

### Delete a Key

```bash
curl -X DELETE http://localhost:8000/admin/keys/ADMIN_KEY_ID \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🎯 Common Workflows

### Workflow 1: Onboard a New Farmer

1. **Admin gets the simulation server key:**
   ```bash
   GET /admin/keys/server/Farmer%20Data%20Source%20Simulation
   ```

2. **Admin generates API token for farmer:**
   ```bash
   POST https://simulation-server.com/admin/keys
   X-Admin-Key: <admin_key>
   Body: {"client_name": "Farmer Name"}
   ```

3. **Admin gives farmer the API key and server URL**

4. **Farmer registers:**
   ```bash
   POST /auth/register
   Body: { ... "server_url": "...", "api_key": "..." }
   ```

### Workflow 2: Update Server URL After ngrok Restart

```bash
# 1. Get the admin key ID
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/admin/keys

# 2. Update the server URL
curl -X PUT http://localhost:8000/admin/keys/KEY_ID \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"server_url": "https://new-ngrok-url.app"}'
```

### Workflow 3: Multiple Environment Support

```bash
# Add dev key
POST /admin/keys
{
  "server_name": "Dev Simulation",
  "admin_key": "dev-key-123...",
  "server_url": "http://localhost:5000"
}

# Add staging key
POST /admin/keys
{
  "server_name": "Staging Simulation",
  "admin_key": "staging-key-456...",
  "server_url": "https://staging.example.com"
}

# Add production key
POST /admin/keys
{
  "server_name": "Production Simulation",
  "admin_key": "prod-key-789...",
  "server_url": "https://prod.example.com"
}
```

## 🐛 Troubleshooting

### Issue: "Admin key not found"

**Solution:** Run the migration and seeding scripts:
```bash
python -m api.run_migration
python -m api.migrate_admin_key
```

### Issue: "403 Forbidden"

**Solution:** Ensure you're logged in as an admin user:
```bash
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/auth/me
# Should return: {"role": "admin"}
```

### Issue: Can't find simulation server .env file

**Solution:** Manually add the key via API:
```bash
curl -X POST http://localhost:8000/admin/keys \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "Farmer Data Source Simulation",
    "admin_key": "PASTE_YOUR_KEY_HERE",
    "is_active": true
  }'
```

## 📚 Full Documentation

For complete details, see [ADMIN_KEY_MANAGEMENT.md](./ADMIN_KEY_MANAGEMENT.md)

## ✅ Testing Checklist

- [ ] Migration creates `admin_keys` table
- [ ] Seeding adds the simulation server key
- [ ] Admin can list all keys
- [ ] Admin can get key by server name
- [ ] Admin can create new keys
- [ ] Admin can update existing keys
- [ ] Admin can delete keys
- [ ] Non-admin users get 403 Forbidden
- [ ] Keys are used successfully to generate farmer tokens
