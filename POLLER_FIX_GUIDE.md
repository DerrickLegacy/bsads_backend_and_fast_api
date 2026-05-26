# Poller Fix Guide

## Problem Summary

The pollers were not working because:
1. **Invalid API keys** - Old data sources had API keys that were rejected by the farmer's server (401 Unauthorized)
2. **Job blocking** - Failed connections caused the `scan_all_sources` job to hang, blocking subsequent runs
3. **Long timeouts** - 30-second timeouts meant failed connections took too long to fail

## What Was Fixed

### 1. Disabled Invalid Data Sources
```sql
UPDATE farmer_data_sources 
SET is_active = false 
WHERE hive_id IN (
    '89448c88-261e-4bf4-8206-b08e0a349fff',
    '4e4c85c5-4a3c-4a1f-ad31-6068e8f8da1b',
    'e2d3a1ac-ac5e-4dc0-9988-9dbe8a79cfcd',
    '814a8709-a39d-452a-a1fb-1d61c05f803c'
);
```

### 2. Improved Error Handling in Poller
- Added try-catch around individual source scans
- One failed source no longer blocks others
- Added logging for scan start/completion

### 3. Reduced HTTP Timeouts
- Changed from 30 seconds to 10 seconds
- Faster failure detection
- Prevents job queue buildup

### 4. Configured Scheduler
- Added `max_instances=1` to prevent overlapping jobs
- Added `coalesce=True` to combine pending runs

## Current Working Configuration

**Active User:**
- Email: `test@example.com`
- API Key: `d3c07d19-cd0d-42b5-88e2-759349a4d023`
- Server URL: `https://jockstrap-boxlike-revisable.ngrok-free.dev/`

**Active Hive:**
- Hive ID: `b33556d2-7f30-4aac-ae38-9076925df80b`
- Hive Name: `Hive 01`

**Data Source:**
- Source ID: `4039f62f-176f-427f-8a82-b7010d44c077`
- Type: `http_api`
- Status: `active`

## How to Add Audio Files

### Folder Structure on Farmer's Server

```
bsads_farmer_external_data_source_simulation/
└── recordings/
    └── d3c07d19-cd0d-42b5-88e2-759349a4d023/  ← API key
        └── b33556d2-7f30-4aac-ae38-9076925df80b/  ← Hive ID
            ├── audio_file_1.wav
            ├── audio_file_2.wav
            └── ...
```

### Commands to Add Files

```bash
# Navigate to farmer's server
cd ~/Desktop/final_year_project/bsads_farmer_external_data_source_simulation

# Create folder structure
mkdir -p recordings/d3c07d19-cd0d-42b5-88e2-759349a4d023/b33556d2-7f30-4aac-ae38-9076925df80b

# Copy audio file
cp /path/to/your/audio.wav recordings/d3c07d19-cd0d-42b5-88e2-759349a4d023/b33556d2-7f30-4aac-ae38-9076925df80b/

# Or copy from old folder
cp recordings/961424ec-94b1-4a00-b9a0-04d948ebd60c/confirmed_swarm_05042026_part2137.wav \
   recordings/d3c07d19-cd0d-42b5-88e2-759349a4d023/b33556d2-7f30-4aac-ae38-9076925df80b/
```

### Verify Files Are Accessible

```bash
curl -H "X-API-Key: d3c07d19-cd0d-42b5-88e2-759349a4d023" \
     "https://jockstrap-boxlike-revisable.ngrok-free.dev/recordings?hive_id=b33556d2-7f30-4aac-ae38-9076925df80b"
```

Expected response:
```json
{
  "recordings": [
    "b33556d2-7f30-4aac-ae38-9076925df80b/audio_file_1.wav",
    "b33556d2-7f30-4aac-ae38-9076925df80b/audio_file_2.wav"
  ],
  "hive_id": "b33556d2-7f30-4aac-ae38-9076925df80b"
}
```

## How the Poller Works

### Two-Phase Process

**Phase 1: Discovery (every 30 seconds)**
1. Scans all active data sources
2. Calls farmer's HTTP API to list recordings
3. Registers new files in database with `status='pending'`
4. Updates `last_scanned_at` timestamp

**Phase 2: Processing (every 30 seconds, offset by 10s)**
1. Queries database for `status='pending'` records
2. Downloads audio bytes from farmer's server
3. Sends to HuggingFace Inference API
4. Stores inference results in database
5. Updates audio source status to `processed` or `failed`

### Status Lifecycle

```
pending → processing → processed
                    ↘ failed
```

## Testing and Monitoring

### Test the Complete Flow

```bash
./venv/bin/python test_poller_flow.py
```

This script:
- ✓ Checks active data sources
- ✓ Tests API connectivity
- ✓ Runs discovery scan manually
- ✓ Shows pending audio sources
- ✓ Shows status breakdown

### Monitor in Real-Time

```bash
./monitor_poller.sh
```

This shows:
- Active data sources and last scan time
- Audio source status counts
- Recent audio sources
- Recent inference results
- Recent system logs

Refreshes every 10 seconds.

### Check System Logs

```bash
PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -c \
  "SELECT level, event_type, message, created_at 
   FROM system_logs 
   WHERE event_type IN ('poller', 'http_api') 
   ORDER BY created_at DESC 
   LIMIT 20;"
```

## Troubleshooting

### Poller Not Finding Files

1. **Check farmer's server is running:**
   ```bash
   curl https://jockstrap-boxlike-revisable.ngrok-free.dev/health
   ```

2. **Verify API key works:**
   ```bash
   curl -H "X-API-Key: d3c07d19-cd0d-42b5-88e2-759349a4d023" \
        "https://jockstrap-boxlike-revisable.ngrok-free.dev/recordings"
   ```

3. **Check folder structure:**
   ```bash
   ls -la ~/Desktop/final_year_project/bsads_farmer_external_data_source_simulation/recordings/d3c07d19-cd0d-42b5-88e2-759349a4d023/b33556d2-7f30-4aac-ae38-9076925df80b/
   ```

4. **Check data source is active:**
   ```bash
   PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -c \
     "SELECT * FROM farmer_data_sources WHERE is_active = true;"
   ```

### Poller Job Stuck

If you see "maximum number of running instances reached":

1. **Restart the API server:**
   - Stop: `Ctrl+C` in the terminal running uvicorn
   - Start: `uvicorn api.main:app --reload --port 8001`

2. **Check for hung processes:**
   ```bash
   ps aux | grep python | grep -E "(poller|uvicorn)"
   ```

### Files Not Processing

1. **Check pending count:**
   ```bash
   PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -c \
     "SELECT COUNT(*) FROM audio_sources WHERE status = 'pending';"
   ```

2. **Check for errors:**
   ```bash
   PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -c \
     "SELECT * FROM system_logs WHERE level = 'error' ORDER BY created_at DESC LIMIT 10;"
   ```

3. **Manually trigger processing:**
   ```python
   from api.poller import process_pending_sources
   process_pending_sources()
   ```

## Adding More Users/Hives

When adding new users and hives:

1. **Register user with server credentials:**
   ```json
   POST /auth/register
   {
     "email": "farmer@example.com",
     "password": "password",
     "full_name": "Farmer Name",
     "server_url": "https://your-ngrok-url.ngrok-free.dev/",
     "api_key": "your-api-key-uuid"
   }
   ```

2. **Create hive:**
   ```json
   POST /hives
   {
     "hive_name": "Hive 01",
     "hive_location": "Location",
     ...
   }
   ```

3. **Data source is auto-created** when hive is created (if user has server credentials)

4. **Create folder on farmer's server:**
   ```bash
   mkdir -p recordings/<api_key>/<hive_id>
   ```

5. **Add audio files** to the folder

6. **Poller will automatically discover** them within 30 seconds

## Files Created

- `test_poller_flow.py` - Comprehensive test script
- `show_folder_structure.sh` - Shows required folder structure
- `monitor_poller.sh` - Real-time monitoring
- `test_farmer_api.py` - API connection diagnostics
- `POLLER_FIX_GUIDE.md` - This guide

## Summary

✅ **Pollers are now working correctly**
✅ **Invalid data sources disabled**
✅ **Better error handling added**
✅ **Timeouts reduced**
✅ **Scheduler configured properly**

**Next step:** Add audio files to the farmer's server in the correct folder structure, and the poller will automatically process them every 30 seconds.
