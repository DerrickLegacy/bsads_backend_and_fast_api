# 🔐 Admin Key & Token Assignment System

## 🎯 What This Solves

**Your Original Problem:**
> "I have to always go to bsads_farmer_external_data_source_simulation .env, copy the ADMIN_KEY, then start this server, and use it to generate a token for beekeepers who wish to start storing their audios."

**Our Solution:**
1. ✅ Admin keys are stored in the database - no more manual copying
2. ✅ Farmers can register without tokens - no waiting
3. ✅ Admins assign tokens with one API call - fully automated
4. ✅ Everything is tracked and auditable

## 🚀 Quick Start

### 1. Run Migrations
```bash
cd bsads_backend_and_fast_api
python3 -m api.run_migration
```

### 2. Start Both Servers
```bash
# Terminal 1: Simulation server
cd bsads_farmer_external_data_source_simulation
uvicorn main:app --reload --port 5000

# Terminal 2: Main backend
cd bsads_backend_and_fast_api
uvicorn api.main:app --reload --port 8000
```

### 3. Configure Admin Key (One-time)
```bash
# Login as admin
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@bsads.ug", "password": "Admin1234"}' \
  | jq -r '.access_token'

# Save the token, then update admin key with ngrok URL
curl -X PUT http://localhost:8000/admin/keys/<admin_key_id> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"server_url": "https://your-ngrok-url.ngrok-free.dev"}'
```

### 4. Test It!
```bash
./test_token_assignment.sh
```

## 📋 New Workflows

### Farmer Registration (No Token Required!)
```bash
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

### Admin Assigns Token
```bash
# 1. Get farmers without tokens
curl -H "Authorization: Bearer <admin_token>" \
  "http://localhost:8000/users?role=farmer" \
  | jq '.[] | select(.api_key == null)'

# 2. Assign token
curl -X POST http://localhost:8000/users/<user_id>/assign-token \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"server_name": "Farmer Data Source Simulation"}'
```

**What happens behind the scenes:**
1. System fetches admin key from database
2. Calls simulation server with farmer's name
3. Simulation server generates API key and stores in `api_keys.json`
4. System updates farmer's record with token and server URL
5. Farmer can now use the system!

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [CHANGES_SUMMARY.md](./CHANGES_SUMMARY.md) | Complete list of all changes |
| [ADMIN_KEY_MANAGEMENT.md](./ADMIN_KEY_MANAGEMENT.md) | Admin key management guide |
| [FARMER_TOKEN_ASSIGNMENT.md](./FARMER_TOKEN_ASSIGNMENT.md) | Token assignment workflow |
| [QUICK_START_ADMIN_KEYS.md](./QUICK_START_ADMIN_KEYS.md) | Admin keys quick start |
| [QUICK_START_TOKEN_ASSIGNMENT.md](./QUICK_START_TOKEN_ASSIGNMENT.md) | Token assignment quick start |

## 🗂️ What Changed

### Database
- ✅ New `admin_keys` table
- ✅ `users.server_url` → Now nullable
- ✅ `users.api_key` → Now nullable

### API Endpoints (New)
- `GET /admin/keys` - List admin keys
- `GET /admin/keys/server/{name}` - Get key by server name
- `POST /admin/keys` - Create admin key
- `PUT /admin/keys/{id}` - Update admin key
- `DELETE /admin/keys/{id}` - Delete admin key
- `POST /users/{id}/assign-token` - Assign farmer token

### API Endpoints (Updated)
- `POST /auth/register` - Now accepts registration without `server_url` and `api_key`

## 🔄 Migration Paths

### If You Have Existing Database
```bash
# 1. Run migrations
python3 -m api.run_migration

# 2. Migrate admin key
python3 -m api.migrate_admin_key

# 3. Restart server
uvicorn api.main:app --reload --port 8000
```

### If Starting Fresh
```bash
# Just start the server - everything auto-seeds!
uvicorn api.main:app --reload --port 8000
```

## ✅ Features

### For Admins
- ✅ View all admin keys in database
- ✅ Update server URLs when ngrok restarts
- ✅ See which farmers need tokens
- ✅ Assign tokens with one click
- ✅ Prevent duplicate token assignments
- ✅ Manage multiple server environments

### For Farmers
- ✅ Register without waiting for tokens
- ✅ Start using system immediately after token assignment
- ✅ No manual configuration needed

### For Developers
- ✅ Automatic seeding on startup
- ✅ Comprehensive error handling
- ✅ Complete API documentation
- ✅ Automated test script
- ✅ Migration scripts included

## 🧪 Testing

### Run Automated Tests
```bash
./test_token_assignment.sh
```

### Manual Testing Steps
1. ✅ Register farmer without token
2. ✅ Verify farmer has `api_key: null`
3. ✅ Assign token via admin endpoint
4. ✅ Verify farmer now has token
5. ✅ Check token exists in simulation server's `api_keys.json`
6. ✅ Try to assign token again (should fail)
7. ✅ Try to access admin endpoints as farmer (should fail)

## 🔒 Security

- ✅ **Role-based access:** Only admins can access admin key endpoints
- ✅ **Duplicate prevention:** Cannot assign token twice
- ✅ **Input validation:** All inputs validated before processing
- ✅ **Error handling:** Clear error messages for all scenarios
- ✅ **Audit trail:** All operations timestamped
- ✅ **Unique constraints:** Admin keys enforced unique in database

## 🐛 Troubleshooting

### "Server URL not configured"
```bash
# Update the admin key
curl -X PUT http://localhost:8000/admin/keys/<id> \
  -H "Authorization: Bearer <token>" \
  -d '{"server_url": "https://your-ngrok-url.ngrok-free.dev"}'
```

### "Simulation server not reachable"
```bash
# Check if simulation server is running
curl http://localhost:5000/health

# If not, start it
cd bsads_farmer_external_data_source_simulation
uvicorn main:app --reload --port 5000
```

### "Admin key not found"
```bash
# Run the migration script
python3 -m api.migrate_admin_key
```

### "Invalid admin key"
The admin key in the database doesn't match the simulation server's `.env`. Update one of them to match.

## 📊 Architecture

```
┌─────────────┐
│   Farmer    │
└─────┬───────┘
      │
      │ 1. Register (no token)
      ▼
┌─────────────┐
│   Backend   │
│     API     │
└─────┬───────┘
      │
      │ 2. Admin assigns token
      ▼
┌─────────────┐         ┌──────────────┐
│  Database   │◄────────│  admin_keys  │
│   users     │         │    table     │
└─────┬───────┘         └──────────────┘
      │                         │
      │ 3. Get admin key        │
      │◄────────────────────────┘
      │
      │ 4. Call simulation server
      ▼
┌─────────────┐
│ Simulation  │
│   Server    │
└─────┬───────┘
      │
      │ 5. Generate & store token
      ▼
┌─────────────┐
│ api_keys    │
│   .json     │
└─────────────┘
```

## 🎯 Benefits

| Before | After |
|--------|-------|
| Manual copying of admin key | Stored in database |
| Farmer must wait for token | Farmer registers immediately |
| Manual token generation | Automatic via API |
| No tracking | Full audit trail |
| ngrok URL changes break things | Easy to update via API |

## 📱 Next Steps

1. ✅ Backend implementation - **DONE**
2. ✅ Documentation - **DONE**
3. ✅ Test script - **DONE**
4. 🔄 Run migrations on your database
5. 🔄 Test the system
6. 📱 Build admin dashboard UI
7. 🚀 Deploy to production

## 💡 Tips

- Update the admin key's `server_url` whenever ngrok restarts
- Use `GET /users?role=farmer` to find farmers without tokens
- The test script will tell you if something is misconfigured
- Check `api_keys.json` to verify tokens were created
- Both old and new registration flows work simultaneously

## 🙏 Support

If you have questions:
1. Check the documentation files
2. Run `./test_token_assignment.sh` to diagnose issues
3. Look at error messages - they're descriptive
4. Verify both servers are running
5. Check the admin key configuration

---

**Ready to get started?** Just run the migrations and test it:

```bash
python3 -m api.run_migration
./test_token_assignment.sh
```

🎉 That's it! Your farmers can now register without tokens, and you can assign them later from the admin dashboard.
