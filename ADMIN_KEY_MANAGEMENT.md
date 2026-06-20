# Admin Key Management System

## Overview

This system automates the management of admin keys for external data source servers, eliminating the need to manually copy keys between projects.

## Problem Solved

**Before:**
- Admins had to manually copy `ADMIN_KEY` from `bsads_farmer_external_data_source_simulation/.env`
- Start the simulation server
- Use the copied key to generate API tokens for farmers
- No centralized storage or management

**After:**
- Admin keys are stored in the database (`admin_keys` table)
- Admins can access keys through the API
- Automatic seeding on startup
- Centralized management with full CRUD operations

## Database Schema

### `admin_keys` Table

```sql
CREATE TABLE admin_keys (
    admin_key_id    UUID PRIMARY KEY,
    server_name     VARCHAR(100) NOT NULL,
    server_url      VARCHAR(255),
    admin_key       VARCHAR(255) NOT NULL UNIQUE,
    description     TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_by      UUID REFERENCES users(user_id),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

## API Endpoints

All endpoints require admin authentication (`role = 'admin'`).

### 1. List All Admin Keys
```http
GET /admin/keys
Authorization: Bearer <admin_token>
```

**Response:**
```json
[
  {
    "admin_key_id": "uuid",
    "server_name": "Farmer Data Source Simulation",
    "server_url": "https://example.ngrok-free.app",
    "admin_key": "128d3e857c80d23134206cbd707300050abc64966a1b5be9c107f8bd7d5b56eb",
    "description": "Default admin key for farmer external data source simulation server",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

### 2. Get Admin Key by ID
```http
GET /admin/keys/{admin_key_id}
Authorization: Bearer <admin_token>
```

### 3. Get Admin Key by Server Name
```http
GET /admin/keys/server/{server_name}
Authorization: Bearer <admin_token>
```

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/admin/keys/server/Farmer%20Data%20Source%20Simulation
```

### 4. Create New Admin Key
```http
POST /admin/keys
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "server_name": "Production Server",
  "server_url": "https://prod.example.com",
  "admin_key": "your-admin-key-here",
  "description": "Production environment admin key",
  "is_active": true
}
```

### 5. Update Admin Key
```http
PUT /admin/keys/{admin_key_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "server_url": "https://new-url.example.com",
  "is_active": false
}
```

### 6. Delete Admin Key
```http
DELETE /admin/keys/{admin_key_id}
Authorization: Bearer <admin_token>
```

## Automatic Seeding

The system automatically seeds the admin key from the simulation server on startup:

1. Reads `ADMIN_KEY` from `../bsads_farmer_external_data_source_simulation/.env`
2. Falls back to `SIMULATION_ADMIN_KEY` environment variable if file not found
3. Creates a database record if the key doesn't already exist
4. Skips if the key is already in the database

### Manual Migration

If automatic seeding fails, run the migration script:

```bash
cd bsads_backend_and_fast_api
python -m api.migrate_admin_key
```

## Usage Flow

### For Admins

1. **Login as admin:**
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@bsads.ug", "password": "Admin1234"}'
   ```

2. **Get the simulation server admin key:**
   ```bash
   curl -H "Authorization: Bearer <admin_token>" \
     http://localhost:8000/admin/keys/server/Farmer%20Data%20Source%20Simulation
   ```

3. **Use the admin key to generate farmer API tokens:**
   ```bash
   curl -X POST https://your-simulation-server.com/admin/keys \
     -H "X-Admin-Key: <admin_key_from_step_2>" \
     -H "Content-Type: application/json" \
     -d '{"client_name": "John Doe"}'
   ```

4. **Give the generated API key to the farmer** for registration

### For Farmers

Farmers register with their server URL and API key:

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
    "server_url": "https://your-simulation-server.com",
    "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }'
```

## Security Considerations

1. **Access Control**: Only users with `role = 'admin'` can access admin key endpoints
2. **Unique Keys**: The database enforces uniqueness on `admin_key` field
3. **Soft Disable**: Keys can be deactivated (`is_active = false`) without deletion
4. **Audit Trail**: Track who created each key via `created_by` field
5. **Environment Separation**: Different keys for dev, staging, and production

## Benefits

✅ **No manual copying** - Keys are automatically seeded and accessible via API  
✅ **Centralized management** - All keys in one place  
✅ **Multi-server support** - Store keys for multiple external servers  
✅ **Audit trail** - Track who created and modified keys  
✅ **Role-based access** - Only admins can access keys  
✅ **Flexible updates** - Change server URLs and deactivate keys without deletion  

## Troubleshooting

### Key Not Found After Startup

1. Check if the simulation server `.env` file exists:
   ```bash
   ls -la ../bsads_farmer_external_data_source_simulation/.env
   ```

2. Verify the `ADMIN_KEY` is present:
   ```bash
   grep ADMIN_KEY ../bsads_farmer_external_data_source_simulation/.env
   ```

3. Run manual migration:
   ```bash
   python -m api.migrate_admin_key
   ```

### Can't Access Admin Key Endpoints

- Ensure you're logged in as an admin user
- Check your token is valid:
  ```bash
  curl -H "Authorization: Bearer <token>" http://localhost:8000/auth/me
  ```
- Verify the response shows `"role": "admin"`

### Adding Keys for Multiple Servers

You can add multiple admin keys for different environments:

```bash
# Development
POST /admin/keys
{
  "server_name": "Dev Simulation Server",
  "server_url": "http://localhost:5000",
  "admin_key": "dev-key-123...",
  "is_active": true
}

# Production
POST /admin/keys
{
  "server_name": "Production Simulation Server",
  "server_url": "https://prod.example.com",
  "admin_key": "prod-key-456...",
  "is_active": true
}
```

## Next Steps

1. ✅ Database model created (`AdminKey`)
2. ✅ API endpoints implemented (`/admin/keys`)
3. ✅ Automatic seeding on startup
4. ✅ Migration script for manual seeding
5. 🔄 Run database migrations
6. 🔄 Test the endpoints
7. 📱 Add admin key management to the mobile/web app UI
