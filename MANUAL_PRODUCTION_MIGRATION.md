# Manual Production Migration Steps

Since you don't have sudo privileges and prefer to run commands manually on the server, follow these steps:

## Step 1: Copy Files to Server

From your **local machine**, copy the migration file:

```bash
scp migrations/add_circuit_breaker_to_data_sources.sql ademneadev@196.43.168.57:/tmp/
```

**Optional**: Also copy the helper script (makes it easier):
```bash
scp apply_migration_on_server.sh ademneadev@196.43.168.57:/tmp/
```

## Step 2: SSH to Production Server

```bash
ssh ademneadev@196.43.168.57
```

## Step 3: Apply Migration

### Option A: Use the Helper Script (Easier)
```bash
cd /tmp
bash apply_migration_on_server.sh
```

### Option B: Run Commands Manually

```bash
# 1. Verify container is running
docker ps | grep bsads-api-production

# 2. Apply the migration
docker exec bsads-api-production psql -U bee_user -d bee_db -f /tmp/add_circuit_breaker_to_data_sources.sql

# 3. Copy migration into container (for records)
docker cp /tmp/add_circuit_breaker_to_data_sources.sql bsads-api-production:/app/migrations/

# 4. Verify column was added
docker exec bsads-api-production psql -U bee_user -d bee_db -c "\d farmer_data_sources" | grep last_error_at

# Should show:
# last_error_at | timestamp without time zone | | |

# 5. Restart container to load new model
docker restart bsads-api-production

# 6. Wait for restart (about 10 seconds)
sleep 10

# 7. Check container is running
docker ps | grep bsads-api-production

# 8. Check logs for any errors
docker logs bsads-api-production --tail 50
```

## Step 4: Verify Everything Works

```bash
# Test health endpoint
curl http://localhost:8085/health

# Should return: {"status":"ok"}

# Monitor the poller (press Ctrl+C to exit)
docker logs -f bsads-api-production | grep poller

# You should see successful scans like:
# "🔍 Discovery poller: scanning X active data sources (concurrent)"
# "✓ Discovery poller: completed scan"
#
# NOT errors like:
# "column farmer_data_sources.last_error_at does not exist"
```

## Step 5: Check Data Sources Status

From your **local machine**, test the new admin endpoint:

```bash
# First, get an admin token by logging in
curl -X POST http://196.43.168.57:8085/bsads-api-db/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@bsads.ug","password":"Admin1234"}'

# Use the token to check data sources status
curl -H "Authorization: Bearer <YOUR_TOKEN>" \
  http://196.43.168.57:8085/admin/data-sources/status
```

## Expected Results

After successful migration, you should see:

1. ✅ No `UndefinedColumn` errors in logs
2. ✅ Poller running successfully every 60 seconds
3. ✅ `last_error_at` column exists in database
4. ✅ Container running without crashes

## Troubleshooting

### Container Not Running
```bash
docker ps -a | grep bsads-api-production
docker logs bsads-api-production --tail 100
```

### Migration Already Applied
If you see "column already exists", that's OK - the migration is idempotent.

### Still Getting Errors
Check that the container was restarted after the migration:
```bash
docker restart bsads-api-production
docker logs -f bsads-api-production
```

## Cleanup (Optional)

After successful migration:
```bash
rm /tmp/add_circuit_breaker_to_data_sources.sql
rm /tmp/apply_migration_on_server.sh
```

## Future Deployments

After this one-time manual fix, all future deployments via GitHub Actions will automatically include this migration. You won't need to apply it manually again.

---

**Time Required**: ~2 minutes  
**Risk Level**: Low (migration is idempotent and only adds a column)  
**Rollback**: Drop the column if needed: `ALTER TABLE farmer_data_sources DROP COLUMN last_error_at;`
