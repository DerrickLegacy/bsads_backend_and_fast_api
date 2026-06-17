# Pre-Push Deployment Checklist ✅

## Files Updated and Ready

### ✅ Core Fixes
- [x] **`api/http_connector.py`** - URL translation for Docker (196.43.168.57 → host.docker.internal)
- [x] **`.github/workflows/deploy.yml`** - Added `--add-host=host.docker.internal:host-gateway` and `-p 8085:8085`
- [x] **`Dockerfile.production`** - EXPOSE 8085, health check on 8085
- [x] **`.env.production`** - PORT=8085
- [x] **`start_production.sh`** - Default port 8085

### ✅ GitHub Secrets Required

Make sure these secrets are configured in your GitHub repository:
- `DOCKERHUB_USERNAME` - Your Docker Hub username
- `DOCKERHUB_TOKEN` - Your Docker Hub access token
- `SERVER_PASSWORD` - SSH password for ademneadev@196.43.168.57
- `SECRET_KEY` - JWT secret key for production
- `HF_SPACE_NAME` - HuggingFace space name
- `HF_TOKEN` - HuggingFace API token

To check: Go to GitHub repo → Settings → Secrets and variables → Actions

---

## Deployment Steps

### 1. Commit and Push
```bash
git add .
git commit -m "Fix Docker networking and port mapping for production deployment"
git push origin main
```

### 2. Monitor GitHub Actions
- Go to: https://github.com/YOUR_USERNAME/YOUR_REPO/actions
- Watch the "Deploy to Production Server" workflow
- Should complete in ~5-10 minutes

### 3. Verify Deployment

After the workflow completes, SSH to your server and run:

```bash
# Check container is running
docker ps | grep bsads-api-production
# Should show: 0.0.0.0:8085->8085/tcp

# Check host.docker.internal is configured
docker exec bsads-api-production cat /etc/hosts | grep host.docker.internal
# Should show: <IP>    host.docker.internal

# Check logs for URL translation
docker logs bsads-api-production 2>&1 | grep "Translating"
# Should show: 🔄 Translating 196.43.168.57 → host.docker.internal

# Test API health
curl http://196.43.168.57:8085/health
# Should return: {"status":"ok","service":"BSADS API"}

# Test connection to simulation server from inside container
docker exec bsads-api-production curl -v http://host.docker.internal:8086/health
# Should succeed (not timeout)
```

---

## What the Deployment Will Do

1. **Build** the Docker image with the new `http_connector.py` code
2. **Push** to Docker Hub as `bsads2026/bsads-api:latest`
3. **SSH** to your production server (196.43.168.57)
4. **Pull** the latest image
5. **Stop** the old container
6. **Start** a new container with:
   - Port mapping: `-p 8085:8085`
   - Host gateway: `--add-host=host.docker.internal:host-gateway`
   - All environment variables
   - Persistent volumes for database and uploads

---

## Expected Results

### ✅ Before (Current - Broken)
```
Connection to 196.43.168.57 timed out (connect timeout=10)
"folder_created": false
"folder_creation_error": "Connection failed..."
```

### ✅ After (Fixed)
```
🔄 Translating 196.43.168.57 → host.docker.internal (same-host detection)
"folder_created": true
"folder_creation_error": null
```

---

## Troubleshooting

### If deployment fails:

1. **Check GitHub Actions logs** for the error
2. **Check GitHub Secrets** are all configured correctly
3. **Check server SSH access**: `ssh ademneadev@196.43.168.57`
4. **Check Docker Hub credentials** are valid

### If deployment succeeds but still getting timeouts:

1. **Check if new image is actually running:**
   ```bash
   docker exec bsads-api-production python -c "from api.http_connector import _translate_localhost_url; print(_translate_localhost_url('http://196.43.168.57:8086'))"
   ```
   Should print: `http://host.docker.internal:8086`

2. **Check simulation server is running:**
   ```bash
   curl http://localhost:8086/health
   ```

3. **Manual database update (fallback):**
   ```bash
   docker exec -it bsads-api-production bash
   psql $DATABASE_URL -f update_server_url.sql
   ```

---

## Alternative: Manual Deployment

If GitHub Actions fails, you can deploy manually:

```bash
# On your local machine
docker build -t bsads2026/bsads-api:latest -f Dockerfile.production .
docker push bsads2026/bsads-api:latest

# SSH to server
ssh ademneadev@196.43.168.57

# Run the fix script
docker stop bsads-api-production && docker rm bsads-api-production
docker pull bsads2026/bsads-api:latest

docker run -d \
  --name bsads-api-production \
  --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  -p 8085:8085 \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="your-secret-key" \
  -e HF_SPACE_NAME="DerrickLegacy256/bee-audio-classifier" \
  -e HF_TOKEN="your-hf-token" \
  -e PORT=8085 \
  bsads2026/bsads-api:latest
```

---

## Summary

Your code is **ready to deploy**! 🚀

All fixes are in place:
- ✅ Port mapping (8085:8085)
- ✅ Docker host gateway configuration
- ✅ Automatic URL translation in code
- ✅ GitHub Actions workflow updated

Just **commit and push to main**, and the deployment will happen automatically!
