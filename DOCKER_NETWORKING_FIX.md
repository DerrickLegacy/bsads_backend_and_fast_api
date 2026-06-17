# Docker Networking Fix for Same-Host Communication

## Problem

Your BSADS API container cannot reach the farmer simulation server at `http://196.43.168.57:8086` because both services are on the **same physical machine**. When inside a Docker container, trying to connect to the host's external IP results in connection timeouts.

### Error Message
```
Connection failed: HTTPConnectionPool(host='196.43.168.57', port=8086): 
Max retries exceeded with url: /recordings/hives/Hive%2001 
(Caused by ConnectTimeoutError(...'Connection to 196.43.168.57 timed out.'))
```

## Root Cause

Docker containers have their own isolated network. When a container tries to reach `196.43.168.57:8086`, it attempts to route through the external network, which fails because:
1. The port might not be accessible via external IP from inside the container
2. Docker's network isolation prevents direct host communication via external IP
3. You need to use Docker's host gateway mechanism instead

## Solution

Use the `--add-host=host.docker.internal:host-gateway` flag when starting the container. This creates a DNS alias that points to the Docker host's internal gateway IP, allowing containers to reach services running on the host.

### Updated Code

I've updated the following files:

1. **`api/http_connector.py`** - Automatically translates `196.43.168.57` → `host.docker.internal` when running inside Docker
2. **`.github/workflows/deploy.yml`** - Added `--add-host` flag to the docker run command
3. **`redeploy_with_port_fix.sh`** - Added `--add-host` flag to the manual deployment script

## Immediate Fix (Manual on Server)

SSH into your server and run these commands:

```bash
# Stop and remove the current container
docker stop bsads-api-production
docker rm bsads-api-production

# Start with both port mapping AND host networking fix
docker run -d \
  --name bsads-api-production \
  --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  -p 8085:8085 \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="your-secret-key-here" \
  -e HF_SPACE_NAME="DerrickLegacy256/bee-audio-classifier" \
  -e HF_TOKEN="your-hf-token-here" \
  -e PORT=8085 \
  bsads2026/bsads-api:latest

# Wait for it to start
sleep 15

# Check the logs
docker logs -f bsads-api-production
```

### Important Note

The key addition is: `--add-host=host.docker.internal:host-gateway`

This tells Docker to:
1. Add a DNS entry for `host.docker.internal`
2. Point it to the special `host-gateway` IP (the Docker host)
3. Allow the container to reach services on the host

## How the Automatic Translation Works

The updated `http_connector.py` now:

1. **Detects Docker environment** by checking for `/.dockerenv`
2. **Checks if running in Docker** and if the URL targets the host
3. **Automatically translates** URLs like:
   - `http://196.43.168.57:8086` → `http://host.docker.internal:8086`
   - `http://localhost:8086` → `http://host.docker.internal:8086`
   - `http://127.0.0.1:8086` → `http://host.docker.internal:8086`

This means **no changes to user data are needed**! The farmer's server URL can remain `http://196.43.168.57:8086/` in the database.

## Testing After Fix

### 1. Test API Health
```bash
curl http://196.43.168.57:8085/health
# Should return: {"status":"ok","service":"BSADS API"}
```

### 2. Create a Hive (should create folder on simulation server)
```bash
curl -X 'POST' \
  'http://196.43.168.57:8085/bsads-api-db/hives' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
  "hive_location": "Test Location",
  "hive_type": "Box",
  "hive_name": "Test Hive 01",
  "installation_date": "2026-06-17",
  "latitude": 0.390332,
  "longitude": 0.9867365,
  "owner_id": "YOUR_USER_ID"
}'
```

### 3. Check Container Logs
```bash
docker logs -f bsads-api-production
```

You should now see:
- `🔄 Translating 196.43.168.57 → host.docker.internal (same-host detection)`
- No more connection timeout errors
- Successful folder creation: `"folder_created": true`

### 4. Verify host.docker.internal is configured
```bash
docker exec -it bsads-api-production cat /etc/hosts | grep host.docker.internal
# Should show: X.X.X.X    host.docker.internal
```

## Alternative Solutions (if the above doesn't work)

### Option A: Use Host Network Mode (Less Isolated)
```bash
docker run -d \
  --name bsads-api-production \
  --restart unless-stopped \
  --network host \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e PORT=8085 \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="your-secret-key" \
  -e HF_SPACE_NAME="DerrickLegacy256/bee-audio-classifier" \
  -e HF_TOKEN="your-hf-token" \
  bsads2026/bsads-api:latest
```

**Pros:** Container can access all host ports directly  
**Cons:** Less network isolation, no port mapping needed (`-p` flag won't work)

### Option B: Update User Server URL to use host.docker.internal

Manually update the database:
```sql
UPDATE users 
SET server_url = 'http://host.docker.internal:8086/' 
WHERE server_url = 'http://196.43.168.57:8086/';
```

**Pros:** Explicit configuration  
**Cons:** Requires database changes, less portable

## Verification Checklist

- [ ] Container is running: `docker ps | grep bsads-api-production`
- [ ] Port mapping shows: `0.0.0.0:8085->8085/tcp`
- [ ] Host gateway configured: `docker exec bsads-api-production cat /etc/hosts | grep host.docker.internal`
- [ ] API responds: `curl http://196.43.168.57:8085/health`
- [ ] Simulation server responds from container: `docker exec bsads-api-production curl http://host.docker.internal:8086/health`
- [ ] No connection timeout errors in logs: `docker logs bsads-api-production 2>&1 | grep -i timeout`
- [ ] Folder creation succeeds when creating hive

## Future Deployments

The GitHub Actions workflow is now updated. Next time you push to `main`, it will automatically:
1. Build the new image with the URL translation code
2. Deploy with `--add-host=host.docker.internal:host-gateway`
3. Work correctly with same-host communication

## Summary

The fix involves two changes:
1. **Container configuration**: Add `--add-host=host.docker.internal:host-gateway` flag
2. **Automatic URL translation**: Updated `http_connector.py` to detect and translate host IPs to `host.docker.internal`

Both the API and simulation server can now communicate even though they're on the same physical machine!
