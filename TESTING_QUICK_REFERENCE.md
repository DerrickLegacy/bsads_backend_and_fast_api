# IoT Device Integration - Quick Testing Reference

## 🎯 Which Server for What?

| Action | Server | Port | Example URL |
|--------|--------|------|-------------|
| **Device uploads CSV** | Simulation | 8086 | `http://localhost:8086/conditions/hives/Hive01/upload` |
| **Device uploads Audio** | Simulation | 8086 | `http://localhost:8086/recordings/hives/Hive01/upload` |
| **Backend polls** | Simulation | 8086 | Automatic (every 2 min) |
| **Backend writes to DB** | Backend | 8003 | Automatic |
| **Check backend logs** | Backend | 8003 | `docker logs bsads-backend` |

---

## 🚀 Quick Test (Manual)

### 1. Upload CSV to Simulation Server

```bash
# Create test CSV
cat > test.csv << 'EOF'
Date,Temperature,Humidity
2026-06-20 14:00:00,28.5*34.2*25.1,60.3*75.0*45.2
EOF

# Upload (use YOUR API key and hive name)
curl -X POST \
  'http://localhost:8086/conditions/hives/Hive01/upload' \
  -H 'x-api-key: YOUR_API_KEY_HERE' \
  -F 'file=@test.csv'

# Expected: 201 Created
```

### 2. Wait for Backend Poller

```bash
# Backend polls every 2 minutes
# Wait 2-3 minutes, then check logs:
docker logs bsads-backend | grep conditions_poller | tail -20
```

### 3. Verify Database

```bash
docker exec -it bsads-db psql -U postgres -d bsads -c \
  "SELECT * FROM hive_conditions ORDER BY created_at DESC LIMIT 5;"
```

---

## 🤖 Automated Test Script

### Run the test script:

```bash
cd /home/derrick-ahaabwe/Desktop/final_year_project/combo2/bsads_backend_and_fast_api

# Get your farmer's API key first (from database or admin panel)
./test_device_integration.sh YOUR_FARMER_API_KEY Hive01
```

**What it does**:
1. Creates test CSV with current timestamp
2. Uploads CSV to simulation server (port 8086)
3. Optionally uploads test audio (if ffmpeg available)
4. Waits 130 seconds for backend poller
5. Checks database for new records
6. Shows backend logs

---

## 🔍 Debugging

### Check if files are on simulation server:

```bash
# List all recordings for a hive
curl -H 'x-api-key: YOUR_API_KEY' \
  'http://localhost:8086/recordings?hive_name=Hive01'
```

### Check backend poller is running:

```bash
# Should see logs every 2 minutes
docker logs -f bsads-backend | grep conditions_poller
```

### Check database directly:

```bash
# Count total records
docker exec -it bsads-db psql -U postgres -d bsads -c \
  "SELECT COUNT(*) FROM hive_conditions;"

# See latest records
docker exec -it bsads-db psql -U postgres -d bsads -c \
  "SELECT hive_id, temp_honey, recorded_at FROM hive_conditions ORDER BY created_at DESC LIMIT 10;"
```

---

## 📊 Server Ports Reference

| Server | Port | Purpose |
|--------|------|---------|
| **Simulation Server** | 8086 | Receives device uploads, stores files |
| **Backend Server** | 8003 | Polls simulation, processes data, writes to DB |
| **PostgreSQL** | 5432 | Database (internal) |

---

## ⚠️ Common Issues

### "Invalid API key" (401)
- **Problem**: Wrong API key or not assigned to farmer
- **Solution**: Check admin panel or database: `SELECT api_key FROM users WHERE email='farmer@example.com';`

### "Hive not found" (404)
- **Problem**: Hive name doesn't match exactly (case-sensitive)
- **Solution**: Check: `SELECT hive_name FROM hives WHERE owner_id='USER_ID';`

### No records in database after waiting
- **Problem**: Backend poller might not be running or erroring
- **Solution**: Check logs: `docker logs bsads-backend | grep -E "conditions_poller|ERROR"`

### Duplicate records appearing
- **Problem**: Deduplication not working (should not happen)
- **Solution**: Check constraint exists: `\d hive_conditions` in psql (should show UNIQUE constraint)

---

## 📝 CSV Format Reminder

```csv
Date,Temperature,Humidity
2026-06-20 14:00:00,28.5*34.2*25.1,60.3*75.0*45.2
```

- **Date**: `YYYY-MM-DD HH:MM:SS` (exact format)
- **Temperature**: `honey*brood*exterior` (in Celsius)
- **Humidity**: `honey*brood*exterior` (in percentage)

---

## 🎓 Understanding the Flow

```
STEP 1: Device → Simulation Server (Port 8086)
  └─> Device uploads CSV/audio
  └─> Gets 201 response instantly
  └─> Device goes to sleep

STEP 2: Backend polls Simulation Server (every 2 min)
  └─> Backend: "What files do you have for Hive01?"
  └─> Simulation: "Here are 3 CSV files"
  └─> Backend downloads and processes each file

STEP 3: Backend → Database
  └─> Parses CSV rows
  └─> Checks for duplicates (hive_id + recorded_at)
  └─> Inserts only NEW records
  └─> Links to audio files by timestamp
```

---

## 📞 Quick Help

| Want to... | Command |
|------------|---------|
| See what files are uploaded | `curl -H 'x-api-key: KEY' http://localhost:8086/recordings?hive_name=HIVE` |
| Check if poller is running | `docker logs bsads-backend \| grep conditions_poller \| tail -5` |
| See latest DB records | `docker exec -it bsads-db psql -U postgres -d bsads -c "SELECT * FROM hive_conditions ORDER BY created_at DESC LIMIT 5;"` |
| Check farmer's credentials | `docker exec -it bsads-db psql -U postgres -d bsads -c "SELECT email, server_url, api_key FROM users WHERE role='farmer';"` |
| Restart backend | `docker restart bsads-backend` |

---

## ✅ Success Indicators

You'll know it's working when you see:

1. **Upload success**: `201 Created` response from simulation server
2. **Poller logs**: `conditions_poller: processing X farmers` in backend logs
3. **Database records**: New rows in `hive_conditions` table
4. **No errors**: No ERROR or WARNING in backend logs

---

For detailed information, see `DEVICE_INTEGRATION_GUIDE.md`
