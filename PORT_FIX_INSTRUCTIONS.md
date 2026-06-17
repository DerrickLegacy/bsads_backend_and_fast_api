# Port Mapping Fix Instructions

## Problem Summary

Your FastAPI application is running correctly **inside** the container on port **8085**, but the port was not properly exposed to the host machine. This is why you got an empty response when accessing `http://196.43.168.57:8085/`.

### Root Cause
The Docker container was started **without the `-p` flag** to map the internal port 8085 to the external port 8085:
```bash
# ❌ WRONG (current setup - no port mapping)
docker run -d --name bsads-api-production ... bsads2026/bsads-api:latest

# ✅ CORRECT (what it should be)
docker run -d --name bsads-api-production -p 8085:8085 ... bsads2026/bsads-api:latest
```

## Files Updated

I've fixed the following files to ensure consistency:

1. **`Dockerfile.production`**
   - Changed `EXPOSE 8080` → `EXPOSE 8085`
   - Updated healthcheck to use port 8085

2. **`.env.production`**
   - Changed `PORT=8080` → `PORT=8085`

3. **`start_production.sh`**
   - Updated default port from 8080 → 8085

4. **`.github/workflows/deploy.yml`**
   - Added `-p 8085:8085` port mapping to the docker run command

## Immediate Fix (Manual on Server)

### Option A: Quick Fix Script (Recommended)

1. Copy the `redeploy_with_port_fix.sh` script to your server:
   ```bash
   scp redeploy_with_port_fix.sh ademneadev@196.43.168.57:~/
   ```

2. SSH into your server and run it:
   ```bash
   ssh ademneadev@196.43.168.57
   bash redeploy_with_port_fix.sh
   ```

### Option B: Manual Commands

SSH into your server and run these commands:

```bash
# Stop and remove the current container
docker stop bsads-api-production
docker rm bsads-api-production

# Start with correct port mapping
docker run -d \
  --name bsads-api-production \
  --restart unless-stopped \
  -p 8085:8085 \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="your-secret-key" \
  -e HF_SPACE_NAME="DerrickLegacy256/bee-audio-classifier" \
  -e HF_TOKEN="your-hf-token" \
  -e PORT=8085 \
  bsads2026/bsads-api:latest

# Wait for it to start
sleep 15

# Test it
curl http://196.43.168.57:8085/health
```

## Verification

After applying the fix, test these URLs:

1. **Health Check:** http://196.43.168.57:8085/health
   - Should return: `{"status":"ok","service":"BSADS API"}`

2. **Root Endpoint:** http://196.43.168.57:8085/
   - Should return API information

3. **API Documentation:** http://196.43.168.57:8085/docs
   - Should show interactive Swagger UI

4. **Container Status:**
   ```bash
   docker ps | grep bsads-api-production
   # Should show: 0.0.0.0:8085->8085/tcp
   ```

## Future Deployments

The next time you push to the `main` branch, the GitHub Actions workflow will automatically:
- Build a new Docker image
- Deploy it with the correct port mapping (`-p 8085:8085`)

No manual intervention will be needed!

## Database Credentials

The existing database will be preserved. Current configuration:
- **Host:** localhost (inside container)
- **Port:** 5432 (internal PostgreSQL)
- **Database:** bee_db
- **Username:** bee_user
- **Password:** bee_user
- **Volume:** `bsads-data` (persisted across container restarts)

## Troubleshooting

### Check container logs:
```bash
docker logs -f bsads-api-production
```

### Check if port is accessible:
```bash
# From server
curl http://localhost:8085/health

# From outside
curl http://196.43.168.57:8085/health
```

### Check port mapping:
```bash
docker port bsads-api-production
# Should show: 8085/tcp -> 0.0.0.0:8085
```

### Verify environment variables:
```bash
docker exec bsads-api-production env | grep PORT
# Should show: PORT=8085
```

## Summary

The issue was simply a missing port mapping in the Docker run command. The application was working perfectly inside the container but wasn't accessible from outside. With the `-p 8085:8085` flag added, traffic from the host's port 8085 will be forwarded to the container's port 8085 where FastAPI is listening.
