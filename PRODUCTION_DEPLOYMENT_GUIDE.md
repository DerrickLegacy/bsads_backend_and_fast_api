# Production Deployment Guide

## Current Production Environment

```
Container: bsads-api-production (ba92f88afb9a)
Image: bsads2026/bsads-api:latest
Ports: 8085:8085 (API), 5433:5432 (PostgreSQL)
Status: Up 46 hours (unhealthy)
```

## Changes to Deploy

1. **CSV Conditions Poller** - New poller for hive conditions data
2. **Prediction Details** - Store and return full ML prediction details
3. **HTTP Connector Fixes** - Fixed `CONDITIONS_DIR` → `HIVE_CONDITIONS_DIR`
4. **Database Migration** - Add `prediction_details` JSONB column

## Pre-Deployment Checklist

### ✅ Safety Verification

- ✓ All new database columns are **nullable** (no impact on existing data)
- ✓ New fields in API responses are **optional** (backward compatible)
- ✓ Migrations are **non-destructive** (only adds columns, no deletions)
- ✓ Old records without prediction_details will return `null` (graceful degradation)

## Deployment Steps

### Step 1: Backup Production Database

```bash
# SSH into production server
ssh adev@ademnea

# Backup database before migration
docker exec bsads-api-production pg_dump -U bee_user bee_db > ~/backup_before_deployment_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh ~/backup_before_deployment_*.sql
```

### Step 2: Copy Migration File to Production

From your local machine:

```bash
# Copy migration file to production server
scp ~/Desktop/final_year_project/combo2/bsads_backend_and_fast_api/api/migrations/004_add_prediction_details_to_inference.sql \
    adev@ademnea:/tmp/

# Optional: Copy hive_conditions migration if not already deployed
scp ~/Desktop/final_year_project/combo2/bsads_backend_and_fast_api/api/migrations/003_add_hive_conditions_table.sql \
    adev@ademnea:/tmp/
```

### Step 3: Run Migrations on Production Database

On production server:

```bash
# Check if hive_conditions table exists
docker exec bsads-api-production psql -U bee_user -d bee_db \
  -c "\dt hive_conditions"

# If NOT exists, run migration 003 first
docker exec -i bsads-api-production psql -U bee_user -d bee_db < /tmp/003_add_hive_conditions_table.sql

# Run migration 004 (prediction_details)
docker exec -i bsads-api-production psql -U bee_user -d bee_db < /tmp/004_add_prediction_details_to_inference.sql

# Verify columns were added
docker exec bsads-api-production psql -U bee_user -d bee_db \
  -c "\d inference_results" | grep prediction

docker exec bsads-api-production psql -U bee_user -d bee_db \
  -c "\d hive_conditions"
```

Expected output:
```
prediction_details   | jsonb                       |           |          |
```

### Step 4: Build New Docker Image

From your local machine:

```bash
cd ~/Desktop/final_year_project/combo2/bsads_backend_and_fast_api

# Build new image with updated code
docker build -t bsads2026/bsads-api:v2.0 .

# Tag as latest
docker tag bsads2026/bsads-api:v2.0 bsads2026/bsads-api:latest

# Push to registry
docker push bsads2026/bsads-api:v2.0
docker push bsads2026/bsads-api:latest
```

### Step 5: Deploy to Production

On production server:

```bash
# Pull latest image
docker pull bsads2026/bsads-api:latest

# Stop current container (keeps data)
docker stop bsads-api-production

# Remove old container (data persists in volumes)
docker rm bsads-api-production

# Run new container with same configuration
docker run -d \
  --name bsads-api-production \
  -p 8085:8085 \
  -p 5433:5432 \
  --restart unless-stopped \
  bsads2026/bsads-api:latest

# Check logs
docker logs -f bsads-api-production
```

**IMPORTANT**: Ensure you use the same volume mounts and environment variables as the old container. Check with:

```bash
# Get old container configuration
docker inspect ba92f88afb9a | grep -A 20 "Mounts\|Env"
```

### Step 6: Verify Deployment

```bash
# Check API health
curl http://localhost:8085/health

# Check database connectivity
docker exec bsads-api-production psql -U bee_user -d bee_db -c "SELECT COUNT(*) FROM inference_results;"

# Check for prediction_details column
docker exec bsads-api-production psql -U bee_user -d bee_db \
  -c "SELECT inference_id, hive_state, confidence_score, prediction_details 
      FROM inference_results 
      ORDER BY created_at DESC 
      LIMIT 3;"

# Check conditions poller (should run automatically via scheduler)
docker logs bsads-api-production | grep "conditions_poller"
```

### Step 7: Monitor First Hour

```bash
# Watch logs for errors
docker logs -f --tail 100 bsads-api-production

# Monitor API responses
watch -n 5 'curl -s http://localhost:8085/health | jq'

# Check database connections
docker exec bsads-api-production psql -U bee_user -d bee_db \
  -c "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'bee_db';"
```

## Rollback Plan (If Needed)

### Option 1: Revert to Previous Container

```bash
# Stop new container
docker stop bsads-api-production
docker rm bsads-api-production

# Restore from backup if needed
docker exec -i bsads-api-production-old psql -U bee_user -d bee_db < ~/backup_before_deployment_YYYYMMDD_HHMMSS.sql

# Restart old container
docker start ba92f88afb9a
```

### Option 2: Keep New Container, Remove Migration

```bash
# Remove prediction_details column (if causing issues)
docker exec bsads-api-production psql -U bee_user -d bee_db \
  -c "ALTER TABLE inference_results DROP COLUMN IF EXISTS prediction_details;"
```

## Post-Deployment Validation

### Test CSV Conditions Upload

```bash
# Create test CSV
cat > /tmp/test_conditions.csv << EOF
Date,Temperature,Humidity
2026-06-22 12:00:00,29.5*35.2*26.1,62.3*76.0*47.2
EOF

# Get a valid API key from production
API_KEY=$(docker exec bsads-api-production psql -U bee_user -d bee_db -t \
  -c "SELECT api_key FROM users WHERE role = 'farmer' AND api_key IS NOT NULL LIMIT 1;")

# Test upload
curl -X POST "http://localhost:8086/conditions/hives/Test%20Hive/upload" \
  -H "X-API-Key: ${API_KEY}" \
  -F "file=@/tmp/test_conditions.csv"
```

### Test Alert with Prediction Details

```bash
# Get latest alert
ALERT_ID=$(docker exec bsads-api-production psql -U bee_user -d bee_db -t \
  -c "SELECT alert_id FROM alerts ORDER BY created_at DESC LIMIT 1;")

# Get user token (replace with actual token)
TOKEN="your-auth-token-here"

# Test endpoint
curl -X GET "http://localhost:8085/api/mobile/alerts/${ALERT_ID}" \
  -H "Authorization: Bearer ${TOKEN}" | jq .prediction_details
```

Expected response:
```json
{
  "prediction_details": {
    "predicted_class": "swarming",
    "confidence": 0.95,
    "top_predictions": [
      {"class": "swarming", "confidence": 0.95},
      {"class": "queenbee_present", "confidence": 0.03}
    ]
  }
}
```

Or `null` for old alerts (before deployment).

## Farmer Data Source Container

The farmer data source container also needs updates:

```bash
# On production server
cd /path/to/farmer-data-source

# Pull latest code with CSV fixes
git pull

# Rebuild image
docker build -t bsads2026/farmer-data-source:v2.0 .
docker tag bsads2026/farmer-data-source:v2.0 bsads2026/farmer-data-source:latest

# Push to registry
docker push bsads2026/farmer-data-source:v2.0
docker push bsads2026/farmer-data-source:latest

# Pull on production
docker pull bsads2026/farmer-data-source:latest

# Restart container
docker stop farmer-data-source
docker rm farmer-data-source

docker run -d \
  --name farmer-data-source \
  -p 8086:8000 \
  --restart unless-stopped \
  bsads2026/farmer-data-source:latest
```

## Database Migration Details

### Migration 003: Hive Conditions Table

```sql
CREATE TABLE IF NOT EXISTS hive_conditions (
    condition_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hive_id UUID NOT NULL REFERENCES hives(hive_id) ON DELETE CASCADE,
    audio_id UUID REFERENCES audio_sources(audio_id) ON DELETE SET NULL,
    temp_honey NUMERIC(5,2),
    temp_brood NUMERIC(5,2),
    temp_exterior NUMERIC(5,2),
    humidity_honey NUMERIC(5,2),
    humidity_brood NUMERIC(5,2),
    humidity_exterior NUMERIC(5,2),
    recorded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Migration 004: Prediction Details

```sql
ALTER TABLE inference_results 
ADD COLUMN IF NOT EXISTS prediction_details JSONB;
```

Both migrations are **safe** and **non-destructive**:
- ✅ Only **add** columns (no deletions)
- ✅ All new columns are **nullable**
- ✅ No impact on existing data
- ✅ Can be rolled back safely

## Environment Variables

Ensure these are set in production:

```bash
# Database
DATABASE_URL=postgresql://bee_user:bee_password@localhost:5432/bee_db

# Inference API
HF_SPACE_NAME=your-hf-space-name
INFERENCE_TIMEOUT_SECONDS=120

# Poller schedules
DISCOVERY_INTERVAL_SECONDS=300
INFERENCE_INTERVAL_SECONDS=60
CONDITIONS_INTERVAL_SECONDS=120
```

## Monitoring After Deployment

### Key Metrics to Watch

1. **API Response Times**
   ```bash
   docker logs bsads-api-production | grep "inference_latency_ms"
   ```

2. **Poller Success Rates**
   ```bash
   docker logs bsads-api-production | grep "poller: completed"
   ```

3. **Database Query Performance**
   ```bash
   docker exec bsads-api-production psql -U bee_user -d bee_db \
     -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements 
         ORDER BY mean_exec_time DESC LIMIT 10;"
   ```

4. **Conditions Data Ingestion**
   ```bash
   docker exec bsads-api-production psql -U bee_user -d bee_db \
     -c "SELECT COUNT(*) as total_conditions, 
         MAX(created_at) as latest_record 
         FROM hive_conditions;"
   ```

## Troubleshooting

### Issue: Conditions poller not running

**Solution:**
```bash
# Check scheduler logs
docker logs bsads-api-production | grep "scheduler\|conditions_poller"

# Manually trigger poller
docker exec bsads-api-production python3 -c "
from api.conditions_poller import poll_and_process_conditions
poll_and_process_conditions()
"
```

### Issue: Prediction details not showing in API

**Check:**
```bash
# Verify column exists
docker exec bsads-api-production psql -U bee_user -d bee_db \
  -c "\d inference_results" | grep prediction

# Check recent inferences
docker exec bsads-api-production psql -U bee_user -d bee_db \
  -c "SELECT prediction_details FROM inference_results 
      WHERE created_at > NOW() - INTERVAL '1 hour' 
      LIMIT 5;"
```

**Note:** Only NEW inferences (after deployment) will have prediction_details. Old ones will be `null`.

### Issue: Container unhealthy

**Check:**
```bash
# View health check logs
docker inspect bsads-api-production | jq '.[0].State.Health'

# Check if API responds
curl http://localhost:8085/health
curl http://localhost:8085/docs
```

## Success Criteria

✅ API health endpoint returns `{"status": "ok"}`  
✅ Database migrations applied successfully  
✅ Old alerts still work (with `null` prediction_details)  
✅ New inferences include prediction_details  
✅ Conditions poller running every 2 minutes  
✅ CSV uploads working via farmer data source  
✅ No errors in logs  
✅ All existing data intact  

## Contact & Support

If issues arise:
1. Check logs: `docker logs bsads-api-production`
2. Check database: `docker exec bsads-api-production psql -U bee_user -d bee_db`
3. Rollback if needed (see Rollback Plan above)

---

**Deployment Date**: 2026-06-22  
**Version**: 2.0  
**Backward Compatible**: ✅ Yes  
**Data Loss Risk**: ❌ None (all changes are additive)
