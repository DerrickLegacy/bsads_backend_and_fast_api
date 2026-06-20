# Quick Start: Token Assignment Workflow

## 🚀 Setup (One-Time)

### 1. Run Migrations
```bash
cd bsads_backend_and_fast_api
python -m api.run_migration
```

### 2. Update Admin Key with Server URL
```bash
# Login as admin
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@bsads.ug", "password": "Admin1234"}' \
  | jq -r '.access_token')

# Get admin key ID
ADMIN_KEY_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/admin/keys \
  | jq -r '.[0].admin_key_id')

# Update with your ngrok URL
curl -X PUT http://localhost:8000/admin/keys/$ADMIN_KEY_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server_url": "https://YOUR_NGROK_URL.ngrok-free.dev"
  }'
```

### 3. Start Both Servers
```bash
# Terminal 1: Start simulation server
cd bsads_farmer_external_data_source_simulation
uvicorn main:app --reload --port 5000

# Terminal 2: Start main backend
cd bsads_backend_and_fast_api
uvicorn api.main:app --reload --port 8000
```

## 👤 Farmer Registration (New Flow)

Farmers can now register **without** needing tokens upfront:

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

✅ **No `server_url` or `api_key` needed!**

## 🔧 Admin Assigns Tokens

### Step 1: Login as Admin
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@bsads.ug", "password": "Admin1234"}' \
  | jq -r '.access_token')
```

### Step 2: List Farmers Without Tokens
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/users?role=farmer" \
  | jq '.[] | select(.api_key == null) | {user_id, full_name, email}'
```

**Output:**
```json
{
  "user_id": "abc-123...",
  "full_name": "John Doe",
  "email": "john@example.com"
}
```

### Step 3: Assign Token to Farmer
```bash
USER_ID="abc-123..."  # From step 2

curl -X POST http://localhost:8000/users/$USER_ID/assign-token \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"server_name": "Farmer Data Source Simulation"}'
```

**Response:**
```json
{
  "user_id": "abc-123...",
  "full_name": "John Doe",
  "email": "john@example.com",
  "server_url": "https://your-ngrok.ngrok-free.dev",
  "api_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "assigned_at": "2024-01-01T12:00:00"
}
```

### Step 4: Verify Token in Simulation Server
```bash
# Check api_keys.json
cat bsads_farmer_external_data_source_simulation/data/api_keys.json
```

**Should contain:**
```json
{
  "f47ac10b-58cc-4372-a567-0e02b2c3d479": {
    "client_name": "John Doe",
    "created_at": "2024-01-01T12:00:00"
  }
}
```

## 🔄 Complete Script

Here's a complete script to register a farmer and assign a token:

```bash
#!/bin/bash

# Configuration
BACKEND_URL="http://localhost:8000"
ADMIN_EMAIL="admin@bsads.ug"
ADMIN_PASSWORD="Admin1234"

# Step 1: Login as admin
echo "1️⃣  Logging in as admin..."
TOKEN=$(curl -s -X POST $BACKEND_URL/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASSWORD\"}" \
  | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Failed to login"
  exit 1
fi
echo "✅ Logged in successfully"

# Step 2: Register new farmer
echo ""
echo "2️⃣  Registering new farmer..."
FARMER_EMAIL="farmer$(date +%s)@example.com"
REGISTER_RESPONSE=$(curl -s -X POST $BACKEND_URL/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"full_name\": \"Test Farmer\",
    \"email\": \"$FARMER_EMAIL\",
    \"password\": \"SecurePass123\",
    \"phone\": \"+256700000000\",
    \"address\": \"Kampala, Uganda\",
    \"role\": \"farmer\"
  }")

USER_ID=$(echo $REGISTER_RESPONSE | jq -r '.user.user_id')
if [ "$USER_ID" == "null" ] || [ -z "$USER_ID" ]; then
  echo "❌ Failed to register farmer"
  echo $REGISTER_RESPONSE | jq
  exit 1
fi
echo "✅ Farmer registered: $FARMER_EMAIL"
echo "   User ID: $USER_ID"

# Step 3: Assign token
echo ""
echo "3️⃣  Assigning token to farmer..."
ASSIGN_RESPONSE=$(curl -s -X POST $BACKEND_URL/users/$USER_ID/assign-token \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"server_name": "Farmer Data Source Simulation"}')

API_KEY=$(echo $ASSIGN_RESPONSE | jq -r '.api_key')
SERVER_URL=$(echo $ASSIGN_RESPONSE | jq -r '.server_url')

if [ "$API_KEY" == "null" ] || [ -z "$API_KEY" ]; then
  echo "❌ Failed to assign token"
  echo $ASSIGN_RESPONSE | jq
  exit 1
fi

echo "✅ Token assigned successfully!"
echo ""
echo "📋 Farmer Details:"
echo "   Email: $FARMER_EMAIL"
echo "   User ID: $USER_ID"
echo "   Server URL: $SERVER_URL"
echo "   API Key: $API_KEY"
```

Save as `assign_farmer_token.sh` and run:
```bash
chmod +x assign_farmer_token.sh
./assign_farmer_token.sh
```

## 🎯 Common Tasks

### Update ngrok URL After Restart
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@bsads.ug", "password": "Admin1234"}' \
  | jq -r '.access_token')

ADMIN_KEY_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/admin/keys | jq -r '.[0].admin_key_id')

curl -X PUT http://localhost:8000/admin/keys/$ADMIN_KEY_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"server_url": "https://NEW_NGROK_URL.ngrok-free.dev"}'
```

### Check Which Farmers Need Tokens
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@bsads.ug", "password": "Admin1234"}' \
  | jq -r '.access_token')

curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/users?role=farmer" \
  | jq '[.[] | {name: .full_name, email: .email, has_token: (.api_key != null)}]'
```

### Batch Assign Tokens to All Pending Farmers
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@bsads.ug", "password": "Admin1234"}' \
  | jq -r '.access_token')

# Get all farmers without tokens
USER_IDS=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/users?role=farmer" \
  | jq -r '.[] | select(.api_key == null) | .user_id')

# Assign token to each
for USER_ID in $USER_IDS; do
  echo "Assigning token to $USER_ID..."
  curl -s -X POST http://localhost:8000/users/$USER_ID/assign-token \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"server_name": "Farmer Data Source Simulation"}' \
    | jq '{user_id, full_name, api_key}'
done
```

## 🐛 Troubleshooting

### Error: "Server URL not configured"
```bash
# Update the admin key with server URL
curl -X PUT http://localhost:8000/admin/keys/<admin_key_id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"server_url": "https://your-ngrok.ngrok-free.dev"}'
```

### Error: "Timeout connecting to simulation server"
```bash
# Check if simulation server is running
curl http://localhost:5000/health

# If not running, start it
cd bsads_farmer_external_data_source_simulation
uvicorn main:app --reload --port 5000
```

### Error: "User already has an API key"
This is expected - each user can only have one token. If you need to reassign:
```bash
# Manually update the user
curl -X PUT http://localhost:8000/users/$USER_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"api_key": null, "server_url": null}'

# Then reassign
curl -X POST http://localhost:8000/users/$USER_ID/assign-token \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"server_name": "Farmer Data Source Simulation"}'
```

## 📚 Next Steps

1. ✅ Run migrations
2. ✅ Update admin key with server URL
3. ✅ Test farmer registration without token
4. ✅ Test admin token assignment
5. 📱 Integrate into admin dashboard UI
6. 🧪 Write automated tests

For full details, see [FARMER_TOKEN_ASSIGNMENT.md](./FARMER_TOKEN_ASSIGNMENT.md)
