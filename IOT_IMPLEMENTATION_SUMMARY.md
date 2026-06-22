# IoT Device Integration - Implementation Summary

## ✅ What Was Implemented

### 1. Simulation Server Endpoints (bsads_farmer_external_data_source_simulation)

#### Audio Upload Endpoint
- **Path**: `POST /recordings/hives/{hive_name}/upload`
- **Purpose**: Accepts WAV files from IoT devices
- **Response Time**: < 1 second (device can sleep immediately)
- **Storage**: `/home/farmer/recordings/{api_key}/{hive_name}/*.wav`

#### CSV Conditions Upload Endpoint
- **Path**: `POST /conditions/hives/{hive_name}/upload`
- **Purpose**: Accepts CSV files with temperature/humidity readings
- **Response Time**: < 500ms (device can sleep immediately)
- **Storage**: `/home/farmer/recordings/{api_key}/{hive_name}/conditions/*.csv`
- **Auto-timestamp**: Adds timestamp to filename to prevent conflicts

### 2. Backend Server Polling System (bsads_backend_and_fast_api)

#### Conditions Poller (`api/conditions_poller.py`)
- **Schedule**: Runs every 2 minutes
- **Concurrency**: Processes up to 5 farmers in parallel
- **Features**:
  - Discovers new CSV files on simulation servers
  - Downloads and parses CSV content
  - **Deduplication**: Checks `hive_id + recorded_at` before inserting
  - Batch inserts for efficiency (100 rows per transaction)
  - Links condition records to audio files by timestamp
  - Error handling with detailed logging

#### Integration with Scheduler
- Added to `api/main.py` as scheduled job
- Runs concurrently with existing audio poller
- Uses APScheduler with max_instances=1 (prevents overlaps)

### 3. Database Schema

#### `hive_conditions` Table
```sql
CREATE TABLE hive_conditions (
    condition_id UUID PRIMARY KEY,
    hive_id UUID REFERENCES hives(hive_id) ON DELETE CASCADE,
    audio_id UUID REFERENCES audio_sources(audio_id) ON DELETE SET NULL,
    
    -- Three-zone readings
    temp_honey NUMERIC(5,2),
    temp_brood NUMERIC(5,2),
    temp_exterior NUMERIC(5,2),
    humidity_honey NUMERIC(5,2),
    humidity_brood NUMERIC(5,2),
    humidity_exterior NUMERIC(5,2),
    
    recorded_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(hive_id, recorded_at)  -- Deduplication constraint
);
```

Migration: `api/migrations/003_add_hive_conditions_table.sql`

---

## 📁 Files Modified/Created

### Simulation Server
- ✅ `main.py` - Added CSV upload endpoint

### Backend Server
- ✅ `api/conditions_poller.py` - NEW: CSV polling and processing logic
- ✅ `api/main.py` - Added conditions poller to scheduler
- ✅ `api/models.py` - Added HiveCondition model
- ✅ `api/routers/device_upload.py` - Simplified to optional webhooks
- ✅ `api/migrations/003_add_hive_conditions_table.sql` - NEW migration
- ✅ `requirements.txt` - Already had `requests` (no changes needed)

### Documentation
- ✅ `DEVICE_INTEGRATION_GUIDE.md` - Comprehensive device integration guide
- ✅ `IOT_IMPLEMENTATION_SUMMARY.md` - This file

---

## 🔄 Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Device Upload (Instant Response)                    │
└─────────────────────────────────────────────────────────────┘

Device → Simulation Server
  POST /recordings/hives/Hive01/upload (WAV file)
  POST /conditions/hives/Hive01/upload (CSV file)
  
Response: 201 Created (< 1 second)
  
Device → Sleep Mode (power conservation)

┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Backend Polling (Every 2 minutes)                   │
└─────────────────────────────────────────────────────────────┘

Backend Poller → Simulation Server
  GET /recordings?hive_name=Hive01 (list CSV files)
  GET /recordings/{api_key}/Hive01/conditions/data.csv
  
Backend → Parse CSV
  - Read each row
  - Check if record exists (hive_id + recorded_at)
  - If NEW → Add to batch
  - If DUPLICATE → Skip
  
Backend → Database
  - Batch insert all NEW records
  - Link to audio_id if timestamp matches
  - Report: {processed: 100, new: 30, duplicate: 70}
```

---

## 🎯 Key Features

### 1. Power Optimization
- Device uploads and sleeps immediately
- No waiting for processing
- Minimal power consumption

### 2. Deduplication
- Checks: `hive_id + recorded_at` combination
- Prevents duplicate records on re-upload
- Example: 100 CSV rows → 30 new, 70 duplicate → Insert only 30

### 3. Concurrency
- Processes multiple farmers in parallel (MAX_WORKERS = 5)
- Thread-safe with separate DB sessions
- Batch processing for efficiency

### 4. Error Handling
- Continues processing other rows on CSV parse errors
- Logs all errors with context (hive_id, user_id, row details)
- Graceful degradation (failures don't stop poller)

### 5. Audio Linking
- Automatically links conditions to audio files
- Matches by: `hive_id + recorded_at` timestamp
- Creates complete dataset for analysis

---

## 📝 CSV Format Specification

### Required Structure
```csv
Date,Temperature,Humidity
2026-06-19 21:42:00,28.5*34.2*25.1,60.3*75.0*45.2
```

### Field Details

**Date Column**:
- Format: `YYYY-MM-DD HH:MM:SS`
- Example: `2026-06-19 21:42:00`
- Must be exact format (used for deduplication)

**Temperature Column**:
- Format: `honey*brood*exterior`
- Values in Celsius (°C)
- Example: `28.5*34.2*25.1`
  - 28.5°C = Honey storage zone
  - 34.2°C = Brood rearing zone
  - 25.1°C = External/entrance

**Humidity Column**:
- Format: `honey*brood*exterior`
- Values in percentage (%)
- Example: `60.3*75.0*45.2`
  - 60.3% = Honey storage zone
  - 75.0% = Brood rearing zone
  - 45.2% = External/entrance

---

## 🧪 Testing Instructions

### 1. Deploy Migration

```bash
# Run migration on production
docker exec -it bsads-db psql -U postgres -d bsads < api/migrations/003_add_hive_conditions_table.sql
```

### 2. Test Device Uploads

**Audio Upload**:
```bash
curl -X POST \
  'http://YOUR_SIMULATION_SERVER/recordings/hives/TestHive/upload' \
  -H 'x-api-key: YOUR_FARMER_API_KEY' \
  -F 'file=@10_2026-06-20_140000.wav'
```

**CSV Upload**:
```bash
# Create test CSV
cat > test_conditions.csv << EOF
Date,Temperature,Humidity
2026-06-20 14:00:00,28.5*34.2*25.1,60.3*75.0*45.2
2026-06-20 15:00:00,28.7*34.5*25.3,61.0*75.5*45.5
EOF

curl -X POST \
  'http://YOUR_SIMULATION_SERVER/conditions/hives/TestHive/upload' \
  -H 'x-api-key: YOUR_FARMER_API_KEY' \
  -F 'file=@test_conditions.csv'
```

### 3. Verify Backend Processing

```bash
# Wait 2-3 minutes for poller to run
# Check logs
docker logs bsads-backend | grep "conditions_poller"

# Check database
docker exec -it bsads-db psql -U postgres -d bsads -c \
  "SELECT * FROM hive_conditions ORDER BY created_at DESC LIMIT 10;"
```

### 4. Test Deduplication

```bash
# Upload same CSV twice
curl -X POST 'http://YOUR_SIMULATION_SERVER/conditions/hives/TestHive/upload' \
  -H 'x-api-key: YOUR_FARMER_API_KEY' \
  -F 'file=@test_conditions.csv'

# Wait for poller (2 minutes)

# Upload again
curl -X POST 'http://YOUR_SIMULATION_SERVER/conditions/hives/TestHive/upload' \
  -H 'x-api-key: YOUR_FARMER_API_KEY' \
  -F 'file=@test_conditions.csv'

# Wait for poller (2 minutes)

# Check logs - should show: processed=2, new=0, duplicate=2
docker logs bsads-backend | grep "conditions_poller"
```

---

## 🚀 Deployment Checklist

- [ ] Run migration: `003_add_hive_conditions_table.sql`
- [ ] Push code to repository
- [ ] Deploy simulation server (includes CSV endpoint)
- [ ] Deploy backend server (includes poller)
- [ ] Verify scheduler is running (check logs)
- [ ] Test device uploads (audio + CSV)
- [ ] Verify polling (wait 2-3 minutes, check database)
- [ ] Test deduplication (upload duplicate CSV)
- [ ] Monitor logs for errors
- [ ] Update device firmware with new endpoints

---

## 🔧 Configuration Options

### Polling Frequency

Edit `api/main.py`:
```python
# Change from 2 minutes to 1 minute
_scheduler.add_job(
    poll_and_process_conditions,
    trigger="interval",
    minutes=1,  # <-- Change this
    ...
)
```

### Concurrency

Edit `api/conditions_poller.py`:
```python
MAX_WORKERS = 10  # Increase for more concurrent processing
BATCH_SIZE = 200  # Increase for larger batch inserts
```

### Timeout

Edit `api/conditions_poller.py`:
```python
response = requests.get(url, headers=headers, timeout=30)  # <-- Increase if needed
```

---

## 📊 Monitoring

### Key Metrics

1. **Upload Success Rate**
   - Check simulation server logs for 201 responses
   - Monitor 400/500 errors

2. **Polling Performance**
   - Check backend logs for "conditions_poller" entries
   - Monitor: processed, new, duplicate counts

3. **Database Growth**
   ```sql
   SELECT COUNT(*) FROM hive_conditions;
   SELECT hive_id, COUNT(*) FROM hive_conditions GROUP BY hive_id;
   ```

4. **Latency**
   - Device upload → Simulation server: < 1 second
   - Poller discovery → Database insert: < 30 seconds (at 2-minute interval)

---

## 🐛 Known Issues / Limitations

1. **No Real-time Processing**: Minimum 2-minute delay (by design for efficiency)
2. **CSV File Accumulation**: Old CSV files are not auto-deleted (manual cleanup needed)
3. **No Validation of Sensor Values**: Accepts any numeric values (no min/max checks)
4. **Single Device Per Hive**: Assumes one device per hive (documented requirement)

---

## 🔮 Future Enhancements

- [ ] Add CSV file cleanup (auto-delete processed files older than X days)
- [ ] Add sensor value validation (min/max temperature/humidity thresholds)
- [ ] Add real-time webhook option (immediate processing on upload)
- [ ] Add device battery level monitoring
- [ ] Add data quality metrics (missing readings, sensor failures)
- [ ] Add grafana dashboard for conditions monitoring

---

## 📚 Related Documentation

- `DEVICE_INTEGRATION_GUIDE.md` - Complete device integration guide
- `ADMIN_KEY_MANAGEMENT.md` - Admin key and token assignment
- `FARMER_TOKEN_ASSIGNMENT.md` - Token assignment workflow
- `api/migrations/003_add_hive_conditions_table.sql` - Database migration

---

## Support

For questions or issues, check:
1. Server logs: `docker logs bsads-backend`
2. Database: `docker exec -it bsads-db psql -U postgres -d bsads`
3. This documentation
4. Contact system administrator
