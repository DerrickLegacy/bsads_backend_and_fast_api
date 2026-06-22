# IoT Device Integration Guide

## Architecture Overview

```
┌──────────┐         ┌────────────────────┐         ┌─────────────────┐
│  Device  │ ──────> │  Simulation Server │ <────── │  Backend Server │
│ (Sensor) │  Upload │  (Fast Response)   │  Polls  │  (Processing)   │
└──────────┘         └────────────────────┘         └─────────────────┘
                              │                              │
                              │                              │
                              └─> File Storage               └─> PostgreSQL DB
```

### Design Principles

1. **Device Power Conservation**: Device uploads and immediately goes to sleep
2. **Fast Response**: Simulation server accepts files instantly (< 1 second response)
3. **Asynchronous Processing**: Backend polls and processes files in background
4. **Concurrency & Queuing**: Backend handles traffic bursts gracefully
5. **Deduplication**: Only new records are inserted (prevents duplicates on re-upload)

---

## Device Configuration

### Prerequisites

- Farmer must be registered in the system
- Admin must assign API token to farmer (see ADMIN_KEY_MANAGEMENT.md)
- Device must have network connectivity
- Device must support HTTP POST requests

### Device Endpoints

#### 1. Audio Upload (WAV files)

**Endpoint**: `POST {server_url}/recordings/hives/{hive_name}/upload`

**Headers**:
```
x-api-key: {farmer_api_key}
Content-Type: multipart/form-data
```

**Body**:
```
file: <binary WAV file>
```

**Filename Format**: `HH_YYYY-MM-DD_HHMMSS.wav`
- Example: `10_2026-06-19_214200.wav`
- `HH`: Hive number (10)
- `YYYY-MM-DD`: Date (2026-06-19)
- `HHMMSS`: Time (21:42:00)

**Example cURL**:
```bash
curl -X POST \
  'https://example-server.com/recordings/hives/Hive01/upload' \
  -H 'x-api-key: f47ac10b-58cc-4372-a567-0e02b2c3d479' \
  -F 'file=@10_2026-06-19_214200.wav'
```

**Response (201 Created)**:
```json
{
  "filename": "10_2026-06-19_214200.wav",
  "hive_name": "Hive01",
  "size_bytes": 1048576,
  "uploaded_at": "2026-06-20T14:30:00.123456Z",
  "path": "f47ac10b.../Hive01/10_2026-06-19_214200.wav"
}
```

---

#### 2. Conditions Upload (CSV files)

**Endpoint**: `POST {server_url}/conditions/hives/{hive_name}/upload`

**Headers**:
```
x-api-key: {farmer_api_key}
Content-Type: multipart/form-data
```

**Body**:
```
file: <binary CSV file>
```

**CSV Format**:
```csv
Date,Temperature,Humidity
2026-06-19 21:42:00,28.5*34.2*25.1,60.3*75.0*45.2
2026-06-19 22:42:00,28.7*34.5*25.3,61.0*75.5*45.5
```

**Column Details**:
- **Date**: `YYYY-MM-DD HH:MM:SS` format
- **Temperature**: Three readings separated by asterisks `*`
  - Reading 1: Honey storage zone temperature (°C)
  - Reading 2: Brood rearing zone temperature (°C)
  - Reading 3: External/entrance temperature (°C)
- **Humidity**: Three readings separated by asterisks `*`
  - Reading 1: Honey storage zone humidity (%)
  - Reading 2: Brood rearing zone humidity (%)
  - Reading 3: External/entrance humidity (%)

**Example cURL**:
```bash
curl -X POST \
  'https://example-server.com/conditions/hives/Hive01/upload' \
  -H 'x-api-key: f47ac10b-58cc-4372-a567-0e02b2c3d479' \
  -F 'file=@hive01.csv'
```

**Response (201 Created)**:
```json
{
  "filename": "hive01_20260620_143000.csv",
  "original_filename": "hive01.csv",
  "hive_name": "Hive01",
  "size_bytes": 2048,
  "uploaded_at": "2026-06-20T14:30:00.123456Z",
  "path": "f47ac10b.../Hive01/conditions/hive01_20260620_143000.csv"
}
```

---

## Backend Processing

### Polling Mechanism

The backend server runs scheduled jobs to discover and process files:

1. **Conditions Poller** (runs every 2 minutes):
   - Discovers new CSV files on simulation server
   - Downloads and parses CSV content
   - Implements deduplication (hive_id + recorded_at)
   - Batch inserts new records to database
   - Links condition records to audio files by timestamp

2. **Audio Poller** (existing - runs based on config):
   - Discovers new audio files
   - Downloads audio bytes
   - Sends to ML inference API
   - Creates inference results and advisories

### Deduplication Logic

**CSV Conditions**:
- Checks if record exists by combination of `hive_id + recorded_at`
- If 100 CSV records with 30 new → only inserts 30 new records
- Skips duplicates silently
- Reports: `{processed: 100, new: 30, duplicate: 70}`

**Audio Files**:
- Checks if file path already exists in `audio_sources` table
- Only processes new files
- Prevents duplicate inference runs

### Concurrency Settings

Located in `api/conditions_poller.py`:

```python
MAX_WORKERS = 5        # Concurrent CSV processing workers
BATCH_SIZE = 100       # Process CSV rows in batches
```

Adjust based on your server capacity.

---

## Device Implementation Examples

### Arduino/ESP32 Example (Audio Upload)

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* server_url = "https://example-server.com";
const char* api_key = "f47ac10b-58cc-4372-a567-0e02b2c3d479";
const char* hive_name = "Hive01";

void uploadAudio(const char* filename, uint8_t* audioData, size_t audioSize) {
  HTTPClient http;
  
  String url = String(server_url) + "/recordings/hives/" + hive_name + "/upload";
  http.begin(url);
  http.addHeader("x-api-key", api_key);
  
  // Create multipart form data
  String boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW";
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  
  String body = "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"file\"; filename=\"" + String(filename) + "\"\r\n";
  body += "Content-Type: audio/wav\r\n\r\n";
  
  // Send request
  http.POST(body + String((char*)audioData) + "\r\n--" + boundary + "--\r\n");
  
  int httpCode = http.GET();
  if (httpCode == 201) {
    Serial.println("Audio uploaded successfully");
  } else {
    Serial.println("Upload failed: " + String(httpCode));
  }
  
  http.end();
  
  // Go to sleep immediately
  esp_deep_sleep_start();
}
```

### Python Example (CSV Upload)

```python
import requests
from datetime import datetime

server_url = "https://example-server.com"
api_key = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
hive_name = "Hive01"

def upload_conditions(csv_path):
    url = f"{server_url}/conditions/hives/{hive_name}/upload"
    headers = {"x-api-key": api_key}
    
    with open(csv_path, 'rb') as f:
        files = {'file': ('conditions.csv', f, 'text/csv')}
        response = requests.post(url, headers=headers, files=files)
    
    if response.status_code == 201:
        print("CSV uploaded successfully")
        print(response.json())
    else:
        print(f"Upload failed: {response.status_code}")
        print(response.text)

# Example usage
upload_conditions("hive01.csv")
```

---

## Troubleshooting

### Device Cannot Upload

**Check**:
1. Server URL is correct and reachable
2. API key is valid (use GET /device/status to verify)
3. Hive name matches exactly (case-sensitive)
4. File format is correct (.wav or .csv)
5. Network connectivity is stable

**Common Errors**:

- `401 Unauthorized`: Invalid or expired API key
- `404 Not Found`: Incorrect server URL or hive name
- `409 Conflict`: Audio file with same name already exists
- `400 Bad Request`: Invalid file format or CSV structure

### Backend Not Processing Files

**Check**:
1. Scheduler is running (check server logs for "conditions_poller")
2. Farmer has valid `server_url` and `api_key` in database
3. Hive exists and has correct `hive_name`
4. No network issues between backend and simulation server

**View Logs**:
```bash
# Check conditions poller logs
docker logs bsads-backend | grep "conditions_poller"

# Check database
psql -d bsads -c "SELECT * FROM hive_conditions ORDER BY created_at DESC LIMIT 10;"
```

### Duplicate Records Appearing

**Should Not Happen** - deduplication is built-in. If duplicates appear:

1. Check database unique constraint:
```sql
-- Should exist: unique (hive_id, recorded_at)
SELECT * FROM hive_conditions 
WHERE hive_id = 'xxx' AND recorded_at = '2026-06-19 21:42:00';
```

2. Check poller logs for errors
3. Verify CSV Date format is exactly `YYYY-MM-DD HH:MM:SS`

---

## Database Schema

### `hive_conditions` Table

```sql
CREATE TABLE hive_conditions (
    condition_id UUID PRIMARY KEY,
    hive_id UUID NOT NULL REFERENCES hives(hive_id) ON DELETE CASCADE,
    audio_id UUID REFERENCES audio_sources(audio_id) ON DELETE SET NULL,
    
    -- Three-zone temperature readings (Celsius)
    temp_honey NUMERIC(5,2),
    temp_brood NUMERIC(5,2),
    temp_exterior NUMERIC(5,2),
    
    -- Three-zone humidity readings (percentage)
    humidity_honey NUMERIC(5,2),
    humidity_brood NUMERIC(5,2),
    humidity_exterior NUMERIC(5,2),
    
    recorded_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Deduplication constraint
    UNIQUE(hive_id, recorded_at)
);
```

---

## Performance Considerations

### Upload Performance

- **Audio files**: Typically 100KB - 2MB, upload time < 1 second
- **CSV files**: Typically < 10KB, upload time < 500ms
- Server response time: < 1 second for device to sleep

### Processing Performance

- **Conditions Poller**: Processes 100+ CSV rows per second
- **Concurrency**: Up to 5 farmers processed in parallel
- **Batch Size**: 100 rows inserted per database transaction
- **Poll Frequency**: Every 2 minutes (configurable)

### Scaling Recommendations

For > 100 farmers:
1. Increase `MAX_WORKERS` to 10-15
2. Increase poll frequency to every 1 minute
3. Add database indexes:
```sql
CREATE INDEX idx_hive_conditions_lookup 
ON hive_conditions(hive_id, recorded_at);

CREATE INDEX idx_audio_sources_timestamp 
ON audio_sources(hive_id, captured_at);
```

---

## Testing

### 1. Test Device Upload (Audio)

```bash
# Create test WAV file
ffmpeg -f lavfi -i sine=frequency=1000:duration=5 -ar 44100 test_audio.wav

# Upload
curl -X POST \
  'http://localhost:8003/bsads-api-db/recordings/hives/TestHive/upload' \
  -H 'x-api-key: YOUR_API_KEY' \
  -F 'file=@test_audio.wav'
```

### 2. Test Device Upload (CSV)

```bash
# Create test CSV
cat > test_conditions.csv << EOF
Date,Temperature,Humidity
2026-06-20 14:00:00,28.5*34.2*25.1,60.3*75.0*45.2
2026-06-20 15:00:00,28.7*34.5*25.3,61.0*75.5*45.5
EOF

# Upload
curl -X POST \
  'http://localhost:8003/bsads-api-db/conditions/hives/TestHive/upload' \
  -H 'x-api-key: YOUR_API_KEY' \
  -F 'file=@test_conditions.csv'
```

### 3. Verify Backend Processing

```bash
# Wait 2-3 minutes for poller to run, then check database
docker exec -it bsads-db psql -U postgres -d bsads -c \
  "SELECT * FROM hive_conditions WHERE hive_id = 'YOUR_HIVE_ID' ORDER BY created_at DESC LIMIT 10;"
```

---

## Security Considerations

1. **API Key Protection**: Never hardcode API keys in device firmware
2. **HTTPS Only**: Always use HTTPS in production
3. **Rate Limiting**: Consider adding rate limits to prevent abuse
4. **File Size Limits**: Enforce max file sizes (WAV: 10MB, CSV: 1MB)
5. **Input Validation**: All inputs are validated server-side

---

## Support

For issues or questions:
- Check server logs: `docker logs bsads-backend`
- Check database: Connect to PostgreSQL and query tables
- Review this guide: Especially troubleshooting section
- Contact system administrator with device logs and error messages
