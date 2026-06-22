# Manual Production Deployment Steps

Follow these steps one by one on the production server.

## Current Production Setup
```
Server: adev@ademnea
Container: bsads-api-production (ba92f88afb9a)
Ports: 8085 (API), 5433 (PostgreSQL)
```

---

## Step 1: SSH to Production Server

```bash
ssh adev@ademnea
```

---

## Step 2: Backup Production Database

```bash
# Create backup with timestamp
docker exec bsads-api-production pg_dump -U bee_user bee_db > ~/backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup was created
ls -lh ~/backup_*.sql
```

**✓ Checkpoint**: Backup file should exist and have size > 0

---

## Step 3: Copy Migration Files to Server

On your **local machine**, open a new terminal:

```bash
# Copy migration files
scp ~/Desktop/final_year_project/combo2/bsads_backend_and_fast_api/api/migrations/003_add_hive_conditions_table.sql adev@ademnea:/tmp/

scp ~/Desktop/final_year_project/combo2/bsads_backend_and_fast_api/api/migrations/004_add_prediction_details_to_inference.sql adev@ademnea:/tmp/
```

**✓ Checkpoint**: Files should be in `/tmp/` on production server

---

## Step 4: Run Database Migrations

Back on **production server**:

```bash
# Check if hive_conditions table exists
docker exec bsads-api-production psql -U bee_user -d bee_db -c "\dt hive_conditions"

# If NOT exists, run migration 003
docker exec -i bsads-api-production psql -U bee_user -d bee_db < /tmp/003_add_hive_conditions_table.sql

# Run migration 004 (adds prediction_details column)
docker exec -i bsads-api-production psql -U bee_user -d bee_db < /tmp/004_add_prediction_details_to_inference.sql

# Verify migrations
docker exec bsads-api-production psql -U bee_user -d bee_db -c "\d inference_results" | grep prediction_details
```

**✓ Checkpoint**: Should see `prediction_details | jsonb`

---

## Step 5: Build and Push New Docker Image

On your **local machine**:

```bash
cd ~/Desktop/final_year_project/combo2/bsads_backend_and_fast_api

# Build image
docker build -t bsads2026/bsads-api:v2.0 .

# Tag as latest
docker tag bsads2026/bsads-api:v2.0 bsads2026/bsads-api:latest

# Push to Docker Hub (login if needed)
docker login
docker push bsads2026/bsads-api:v2.0
docker push bsads2026/bsads-api:latest
```

**✓ Checkpoint**: Images should be pushed to Docker Hub

---

## Step 6: Get Current Container Configuration

On **production server**:

```bash
# Save current configuration
docker inspect bsads-api-production > ~/container_config_backup.json

# Check volumes
docker inspect bsads-api-production | grep -A 10 "Mounts"

# Check environment variables
docker inspect bsads-api-production | grep -A 30 "Env"

# Check ports
docker inspect bsads-api-production | grep -A 10 "PortBindings"
```

**Note these down** - you'll need them for the new container.

---

## Step 7: Pull New Image

On **production server**:

```bash
# Pull latest image
docker pull bsads2026/bsads-api:latest

# Verify image
docker images | grep bsads-api
```

**✓ Checkpoint**: New image should be downloaded

---

## Step 8: Stop Old Container (Keep Data!)

On **production server**:

```bash
# Stop container (data persists in volumes/database)
docker stop bsads-api-production

# Rename old container (don't remove yet - for easy rollback)
docker rename bsads-api-production bsads-api-production-old

# Verify it's stopped
docker ps -a | grep bsads-api
```

**✓ Checkpoint**: Old container should be stopped but still exist

---

## Step 9: Start New Container

On **production server**, adjust this command based on your configuration from Step 6:

```bash
docker run -d \
  --name bsads-api-production \
  -p 8085:8085 \
  -p 5433:5432 \
  --restart unless-stopped \
  bsads2026/bsads-api:latest
```

**IMPORTANT**: If your old container had volume mounts or environment variables, add them here. Example:

```bash
docker run -d \
  --name bsads-api-production \
  -p 8085:8085 \
  -p 5433:5432 \
  -v /path/to/data:/data \
  -e DATABASE_URL=postgresql://bee_user:password@localhost:5432/bee_db \
  -e HF_SPACE_NAME=your-space-name \
  --restart unless-stopped \
  bsads2026/bsads-api:latest
```

**✓ Checkpoint**: New container should be running

---

## Step 10: Verify Deployment

On **production server**:

```bash
# Wait a few seconds for startup
sleep 10

# Check container status
docker ps | grep bsads-api-production

# Check logs
docker logs --tail 50 bsads-api-production

# Test API health
curl http://localhost:8085/health

# Should return: {"status":"ok"}

# Test database connectivity
docker exec bsads-api-production psql -U bee_user -d bee_db -c "SELECT COUNT(*) FROM inference_results;"

# Check new column
docker exec bsads-api-production psql -U bee_user -d bee_db \
  -c "SELECT inference_id, hive_state, prediction_details FROM inference_results ORDER BY created_at DESC LIMIT 3;"
```

**✓ Checkpoint**: 
- API returns `{"status":"ok"}`
- Database queries work
- Old records have `NULL` prediction_details (expected)

---

## Step 11: Test Conditions Poller

On **production server**:

```bash
# Check if conditions poller is running (watch logs)
docker logs -f bsads-api-production | grep conditions_poller

# Should see logs like:
# [conditions_poller] 🌡️  Conditions poller: processing X farmers
```

Press `Ctrl+C` to stop watching logs.

**✓ Checkpoint**: Conditions poller should run every 2 minutes

---

## Step 12: Monitor for 15 Minutes

On **production server**:

```bash
# Watch logs for any errors
docker logs -f --tail 100 bsads-api-production

# In another terminal, check API health every 30 seconds
watch -n 30 'curl -s http://localhost:8085/health'
```

**✓ Checkpoint**: No errors in logs, API stays healthy

---

## Step 13: Remove Old Container (Optional)

**Only do this if everything is working perfectly!**

On **production server**:

```bash
# Remove old container
docker rm bsads-api-production-old

# Clean up old images
docker image prune -a
```

---

## Rollback Instructions (If Something Goes Wrong)

On **production server**:

```bash
# Stop new container
docker stop bsads-api-production
docker rm bsads-api-production

# Start old container
docker start bsads-api-production-old
docker rename bsads-api-production-old bsads-api-production

# Restore database if needed
docker exec -i bsads-api-production psql -U bee_user -d bee_db < ~/backup_YYYYMMDD_HHMMSS.sql
```

---

## Update Farmer Data Source (Optional)

If you also want to update the farmer-data-source container:

On **production server**:

```bash
# Pull latest image
docker pull bsads2026/farmer-data-source:latest

# Stop and remove old container
docker stop farmer-data-source
docker rm farmer-data-source

# Start new container
docker run -d \
  --name farmer-data-source \
  -p 8086:8000 \
  -v ./recordings:/home/farmer/recordings \
  -v ./hive_conditions:/home/farmer/hive_conditions \
  -v ./data:/data \
  --restart unless-stopped \
  bsads2026/farmer-data-source:latest

# Verify
curl http://localhost:8086/health
```

---

## Post-Deployment Checklist

✅ API health endpoint working  
✅ Database queries successful  
✅ Old alerts still accessible  
✅ New inferences will have prediction_details  
✅ Conditions poller running  
✅ No errors in logs  
✅ All existing data intact  

---

## Quick Commands Reference

### Check API Status
```bash
curl http://localhost:8085/health
docker logs --tail 50 bsads-api-production
docker ps | grep bsads-api
```

### Check Database
```bash
docker exec bsads-api-production psql -U bee_user -d bee_db -c "SELECT COUNT(*) FROM inference_results;"
docker exec bsads-api-production psql -U bee_user -d bee_db -c "SELECT COUNT(*) FROM hive_conditions;"
```

### Check Logs
```bash
docker logs -f bsads-api-production
docker logs bsads-api-production | grep ERROR
docker logs bsads-api-production | grep conditions_poller
```

### Restart Container
```bash
docker restart bsads-api-production
```

---

## What Changed?

1. **New CSV Conditions Poller** - Automatically fetches temperature/humidity data from IoT devices
2. **Prediction Details** - Stores all ML prediction confidences (top-3) for better insights
3. **Bug Fixes** - Fixed directory references in HTTP connector
4. **Database** - Added 2 new columns (both nullable, no impact on existing data)

All changes are **backward compatible** - existing data is unaffected!

---

**Deployment Time**: ~15-20 minutes  
**Downtime**: ~30 seconds (during container swap)  
**Risk Level**: Low (all changes are additive)
