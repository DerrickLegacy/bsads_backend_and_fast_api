# Railway Migration Guide - Advisory System Restructure

## ⚠️ IMPORTANT: Run Migration BEFORE Deploying New Code

Your Railway production database needs to be migrated to the new advisory system structure before you deploy the updated code.

---

## Step 1: Get Railway DATABASE_URL

1. Go to https://railway.app
2. Open your project
3. Click on the **PostgreSQL** service
4. Click on **Variables** tab
5. Find and copy the `DATABASE_URL` value

It should look like:
```
postgresql://postgres:password@containers-us-west-123.railway.app:1234/railway
```

---

## Step 2: Export DATABASE_URL Locally

In your terminal, run:

```bash
export DATABASE_URL='postgresql://postgres:YOUR_PASSWORD@YOUR_HOST:PORT/railway'
```

(Replace with your actual Railway DATABASE_URL)

---

## Step 3: Run the Migration

```bash
./run_migration_railway.sh migrations/restructure_advisory_system.sql
```

You should see output like:
```
BEGIN
SELECT 0
...
✓ Migration completed successfully!
```

---

## Step 4: Verify Migration

Check that the new tables exist:

```bash
psql "$DATABASE_URL" -c "\dt advisory*"
```

You should see:
```
 advisory_actions    | table
 advisory_templates  | table
 advisories          | table
```

---

## Step 5: Seed Advisory Actions (Optional)

If you want to seed the action library, run:

```bash
psql "$DATABASE_URL" -f migrations/seed_restructured_advisory_data.sql
```

This will populate:
- Advisory templates (9 classifications)
- Advisory library (30+ actions with confidence thresholds)

---

## Step 6: Deploy Updated Code to Railway

Now that the database is migrated, you can safely deploy:

```bash
git add .
git commit -m "Restructure advisory system with confidence-based actions"
git push
```

Railway will automatically redeploy with the new code.

---

## Troubleshooting

### Error: "column min_confidence_threshold does not exist"

This means the migration hasn't been run yet on your Railway database. Go back to Step 2.

### Error: "relation advisory_actions already exists"

This means the migration was already run. You can skip to Step 6.

### Can't connect to Railway database

Make sure:
1. Your DATABASE_URL is correct (copied from Railway dashboard)
2. You have `psql` installed (`sudo apt install postgresql-client`)
3. Your IP is allowed (Railway allows all IPs by default)

---

## What Changes After Migration?

### Before (Old Structure)
- `advisory_templates`: Had classification + advisory text all together
- `advisories`: Generated per inference, copied from template
- `advisory_actions`: Actions within each advisory

### After (New Structure)  
- `advisory_templates`: Classification definitions ONLY (no actions)
- `advisories`: Reusable ACTION LIBRARY for all classifications
- `advisory_actions`: Specific actions suggested per inference based on confidence

### New Behavior
- When inference is created, system automatically:
  1. Looks up classification in `advisory_templates`
  2. Checks confidence threshold
  3. Queries `advisories` for matching actions
  4. Creates `advisory_actions` records for that specific hive

---

## Rollback (If Needed)

If something goes wrong, you can restore from the backup:

```bash
# The migration creates backups automatically:
# - advisory_templates_backup
# - advisories_backup  
# - advisory_actions_backup

# To rollback, contact Railway support or restore from your database backups
```

---

## Need Help?

Check the logs on Railway:
1. Go to your project
2. Click on the **bsads-api** service
3. Click on **Deployments**
4. Click on the latest deployment
5. View logs to see any errors
