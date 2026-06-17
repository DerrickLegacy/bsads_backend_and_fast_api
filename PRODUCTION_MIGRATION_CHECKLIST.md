# 🚨 Production Migration Required: Circuit Breaker Fix

## Problem
The production database is missing the `last_error_at` column in `farmer_data_sources` table, which will cause the poller to crash with:
```
psycopg2.errors.UndefinedColumn: column farmer_data_sources.last_error_at does not exist
```

## What Changed
- Added `last_error_at` column to track connection failures
- Implemented circuit breaker logic to skip failing sources for 10 minutes
- Reduced concurrent workers from 10 to 5 to avoid overwhelming APIs

## Files Changed
- ✅ `migrations/add_circuit_breaker_to_data_sources.sql` - New migration
- ✅ `api/models.py` - Added `last_error_at` field to `FarmerDataSource` model
- ✅ `api/poller_concurrent.py` - Circuit breaker logic + reduced workers
- ✅ `start_production.sh` - Added migration to startup sequence
- ✅ `api/routers/admin_views.py` - Added `/admin/data-sources/status` diagnostic endpoint

## Immediate Action Required (For Current Production)

### Option A: Quick Fix (Recommended)
Run the automated script:
```bash
./apply_migration_to_production.sh
```

This will:
1. Copy the migration to the server
2. Apply it to the production database
3. Restart the container to load the new model
4. Verify the deployment

### Option B: Manual Fix
```bash
# 1. Copy migration to server
scp migrations/add_circuit_breaker_to_data_sources.sql ademneadev@196.43.168.57:/tmp/

# 2. SSH to server and apply
ssh ademneadev@196.43.168.57

# 3. Apply migration
docker exec bsads-api-production psql -U bee_user -d bee_db -f /tmp/add_circuit_breaker_to_data_sources.sql

# 4. Copy migration into container for records
docker cp /tmp/add_circuit_breaker_to_data_sources.sql bsads-api-production:/app/migrations/

# 5. Restart container
docker restart bsads-api-production

# 6. Verify
docker logs bsads-api-production --tail 50
curl http://196.43.168.57:8085/health
```

## Next Deployment (Automatic)

The next `git push` to `main` will automatically:
1. Build new Docker image with the migration
2. Deploy to production
3. Run all migrations including the new one
4. Start the updated application

**No manual intervention needed for future deployments.**

## Verification

After applying the migration, verify it worked:

```bash
# Check database schema
ssh ademneadev@196.43.168.57
docker exec bsads-api-production psql -U bee_user -d bee_db -c "\d farmer_data_sources"

# Should see last_error_at column:
# last_error_at | timestamp without time zone | | |

# Check logs for successful poller runs
docker logs -f bsads-api-production | grep poller

# Should see:
# "Discovery poller: scanning X active data sources (concurrent)"
# NOT: "UndefinedColumn" errors
```

## Testing

After migration, test the system:

1. **Health check:**
   ```bash
   curl http://196.43.168.57:8085/health
   ```

2. **Check data sources status (admin only):**
   ```bash
   curl -H "Authorization: Bearer <admin_token>" \
     http://196.43.168.57:8085/admin/data-sources/status
   ```

3. **Monitor poller:**
   ```bash
   ssh ademneadev@196.43.168.57 'docker logs -f bsads-api-production | grep poller'
   ```

4. **Verify circuit breaker:**
   - Sources that fail will show `last_error_at` timestamp
   - Failed sources will be skipped for 10 minutes
   - No more infinite retry loops

## Rollback Plan

If something goes wrong:

```bash
# 1. Revert to previous container
ssh ademneadev@196.43.168.57
docker stop bsads-api-production
docker rm bsads-api-production
docker run -d --name bsads-api-production [same args as before] <previous_image_tag>

# 2. Remove the column (if needed)
docker exec bsads-api-production psql -U bee_user -d bee_db \
  -c "ALTER TABLE farmer_data_sources DROP COLUMN IF EXISTS last_error_at;"
```

## Timeline

- **Now**: Apply migration to current production (Option A or B above)
- **Next commit**: Automatic deployment will include all changes
- **Future**: All new deployments will have this migration built-in

## Questions?

- Migration file: `migrations/add_circuit_breaker_to_data_sources.sql`
- Migration docs: `migrations/README.md`
- Diagnostic script: `check_data_sources.sh`
- Production script: `apply_migration_to_production.sh`

---

**Status**: ⚠️ **ACTION REQUIRED** - Run the migration script or wait for next deployment
