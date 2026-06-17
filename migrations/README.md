# Database Migrations

This directory contains SQL migration files that are applied automatically during deployment.

## How Migrations Work

### Automatic Application (Production)
Migrations are automatically applied during container startup via `start_production.sh`:
1. Container starts
2. PostgreSQL becomes ready
3. Each migration file is executed in order
4. FastAPI server starts

### Manual Application (Development)
```bash
# Apply a single migration
psql "$DATABASE_URL" -f migrations/<migration_file>.sql

# Check if migration was applied
psql "$DATABASE_URL" -c "\d <table_name>"
```

## Migration Files

| File | Date | Description | Status |
|------|------|-------------|--------|
| `add_user_server_credentials.sql` | 2024 | Add server_url and api_key to users | ✅ Applied |
| `add_soft_delete_to_hives.sql` | 2024 | Add soft delete support to hives table | ✅ Applied |
| `add_timestamps_to_audio_sources.sql` | 2024 | Add created_at/updated_at to audio_sources | ✅ Applied |
| `restructure_advisory_system.sql` | 2024 | Restructure advisory system schema | ✅ Applied |
| `seed_restructured_advisory_data.sql` | 2024 | Seed advisory action library data | ✅ Applied |
| `add_circuit_breaker_to_data_sources.sql` | 2026-06-17 | Add last_error_at for circuit breaker logic | ✅ Applied |

## Adding a New Migration

1. **Create the migration file:**
   ```bash
   touch migrations/<descriptive_name>.sql
   ```

2. **Write idempotent SQL:**
   ```sql
   -- Use IF NOT EXISTS clauses to make migrations safe to re-run
   ALTER TABLE my_table
   ADD COLUMN IF NOT EXISTS my_column TEXT NULL;
   ```

3. **Update the model** (if applicable):
   ```python
   # api/models.py
   class MyModel(Base):
       my_column = Column(Text, nullable=True)
   ```

4. **Add to startup script:**
   ```bash
   # start_production.sh
   echo "📝 Applying my migration..."
   if psql "$DATABASE_URL" -f migrations/<descriptive_name>.sql 2>&1 | grep -v "^$"; then
       echo "✓ Migration completed"
   fi
   ```

5. **Test locally:**
   ```bash
   psql "$DATABASE_URL" -f migrations/<descriptive_name>.sql
   ```

6. **Commit and deploy:**
   ```bash
   git add migrations/<descriptive_name>.sql start_production.sh api/models.py
   git commit -m "Add migration: <description>"
   git push origin main
   ```

## Applying Migration to Existing Production

If production is already running without the migration:

### Option 1: Use the Helper Script (Recommended)
```bash
./apply_migration_to_production.sh
```

### Option 2: Manual SSH
```bash
# Copy migration to server
scp migrations/<file>.sql ademneadev@196.43.168.57:/tmp/

# Apply via Docker exec
ssh ademneadev@196.43.168.57
docker exec bsads-api-production psql -U bee_user -d bee_db -f /tmp/<file>.sql
docker restart bsads-api-production
```

## Troubleshooting

### Migration Already Applied
Migrations use `IF NOT EXISTS` clauses, so re-running is safe and will be skipped.

### Column Already Exists Error
```sql
-- BAD (will fail on second run)
ALTER TABLE my_table ADD COLUMN my_column TEXT;

-- GOOD (idempotent, safe to re-run)
ALTER TABLE my_table ADD COLUMN IF NOT EXISTS my_column TEXT;
```

### Model Out of Sync with Database
1. Check if migration was applied:
   ```bash
   psql "$DATABASE_URL" -c "\d <table_name>"
   ```

2. If missing, apply the migration:
   ```bash
   psql "$DATABASE_URL" -f migrations/<file>.sql
   ```

3. Restart the FastAPI server to reload the model

### Production Migration Failed
1. Check container logs:
   ```bash
   ssh ademneadev@196.43.168.57 'docker logs bsads-api-production --tail 100'
   ```

2. Verify database state:
   ```bash
   ssh ademneadev@196.43.168.57
   docker exec -it bsads-api-production psql -U bee_user -d bee_db
   \d <table_name>
   ```

3. Apply manually if needed (see Option 2 above)

## Best Practices

✅ **DO:**
- Use `IF NOT EXISTS` / `IF EXISTS` clauses
- Add comments explaining why the migration is needed
- Test migrations locally before deploying
- Keep migrations small and focused
- Use descriptive file names with dates

❌ **DON'T:**
- Delete or modify existing migration files
- Use `DROP COLUMN` without careful consideration
- Forget to update the model when changing schema
- Skip testing migrations locally
- Create migrations that depend on specific data

## Migration Order

Migrations are applied in the order listed in `start_production.sh`. 
If a new migration depends on a previous one, ensure it's added after that migration in the script.
