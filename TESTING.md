# BSADS FastAPI — End-to-End Testing Guide

This guide walks through the full system test using the **farmer SSH simulation** Docker container as a stand-in for a real farmer's external sensor server.

---

## What We Are Testing

```
Docker container (farmer simulation)
   /home/farmer/recordings/
       hive1_test.wav  (882 KB)
       hive2_test.wav  (882 KB)
       hive3_test.wav  (882 KB)
           │
           │  SSH/SFTP — paramiko polls every 30 seconds
           ▼
   BSADS FastAPI (localhost:8000)
           │
           │  feature extraction (171 features)
           │  inference via gradient_boosting_model.pkl
           ▼
   PostgreSQL (bee_db)
           │
           ▼
   GET /hives/1/inferences  ← mobile app reads this
```

---

## Prerequisites

1. **BSADS API is running** — see [SETUP.md](SETUP.md)
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

2. **Farmer simulation Docker container is running**
   ```bash
   cd /path/to/bsads_farmer_external_data_source_simulation
   docker compose up -d
   docker compose ps   # farmer-sim should show "Up"
   ```

3. **Verify the SSH server is reachable**
   ```bash
   # Quick connection test using Python
   python3 -c "
   import paramiko
   c = paramiko.SSHClient()
   c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
   c.connect('127.0.0.1', port=2222, username='farmer', password='farmerpass123')
   sftp = c.open_sftp()
   print('Files:', sftp.listdir('/home/farmer/recordings'))
   c.close()
   "
   # Expected: Files: ['hive1_test.wav', 'hive2_test.wav', 'hive3_test.wav']
   ```

---

## Step-by-Step Test

Run these commands in a terminal while the API is running in another window.

### Step 1 — Register a farmer account

```bash
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "fullname": "Test Farmer",
    "email": "farmer@test.ug",
    "password": "pass1234",
    "telephone_number": "+256700000001",
    "role": "farmer"
  }' | python3 -m json.tool
```

Expected response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "user_id": 1,
    "fullname": "Test Farmer",
    "email": "farmer@test.ug",
    "role": "farmer",
    "created_at": "2026-05-03T10:00:00"
  }
}
```

**Copy the `access_token` value** and export it:

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Or capture it automatically:

```bash
export TOKEN=$(curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"fullname":"Test Farmer","email":"farmer@test.ug","password":"pass1234","role":"farmer"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token set: ${TOKEN:0:30}..."
```

---

### Step 2 — Login (if you already registered)

```bash
export TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "farmer@test.ug", "password": "pass1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token set: ${TOKEN:0:30}..."
```

---

### Step 3 — Register a hive

```bash
curl -s -X POST http://localhost:8000/hives \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hive_location": "Kampala, Nakawa Lab",
    "hive_type": "Langstroth",
    "installation_date": "2026-01-15T00:00:00"
  }' | python3 -m json.tool
```

Expected response:

```json
{
  "hive_id": 1,
  "user_id": 1,
  "hive_location": "Kampala, Nakawa Lab",
  "hive_type": "Langstroth",
  "installation_date": "2026-01-15T00:00:00",
  "current_state": "unknown"
}
```

This automatically creates a local watched folder at `data_sources/1/1/` and registers a `FarmerDataSource` record with `source_type=folder`. The next step replaces that with SSH.

---

### Step 4 — Configure the SSH data source

This is the key step. It tells the API where the farmer's external server is and how to connect to it. We use the Docker simulation credentials here.

```bash
curl -s -X POST http://localhost:8000/hives/1/data-source/configure \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_host": "127.0.0.1",
    "ssh_port": 2222,
    "ssh_username": "farmer",
    "ssh_password": "farmerpass123",
    "remote_folder": "/home/farmer/recordings"
  }' | python3 -m json.tool
```

Expected response — includes an immediate connection test result:

```json
{
  "source_id": "a1b2c3d4-...",
  "hive_id": 1,
  "source_type": "ssh",
  "remote_folder": "/home/farmer/recordings",
  "connection_test": {
    "ok": true
  }
}
```

If `connection_test.ok` is `false`, the `error` field will tell you what went wrong (wrong password, host unreachable, folder does not exist, etc.). The config is still saved so you can fix it without re-entering everything.

The `FarmerDataSource` record for hive 1 is now updated to `source_type=ssh` with the credentials stored in `connection_config`.

---

### Step 5 — Check data source status

```bash
curl -s http://localhost:8000/hives/1/data-source \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected response:

```json
{
  "source_id": "a1b2c3d4-...",
  "hive_id": 1,
  "source_type": "ssh",
  "source_path": "/home/farmer/recordings",
  "last_scanned_at": null,
  "is_active": true,
  "created_at": "2026-05-03T10:00:00"
}
```

`last_scanned_at` is `null` because the poller has not run yet. It runs every 30 seconds from when the server started.

---

### Step 6 — Wait for the poller

The poller runs automatically every 30 seconds. Watch the API server logs — you should see:

```
[POLLER/ssh] hive=1 → hive1_test.wav
[POLLER/ssh] hive=1 → hive2_test.wav
[POLLER/ssh] hive=1 → hive3_test.wav
```

Each line means the file was downloaded, inference ran, and the result was stored.

You can also check the data source status again to confirm it was scanned:

```bash
curl -s http://localhost:8000/hives/1/data-source \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# last_scanned_at will now have a timestamp
```

---

### Step 7 — Read inference results

```bash
# All results for hive 1 (last 20)
curl -s http://localhost:8000/hives/1/inferences \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

You should see three results — one per wav file. A normal hive looks like:

```json
[
  {
    "inference_id": "b2c3d4e5-...",
    "hive_id": 1,
    "hive_state": "active_colony",
    "confidence_score": 0.9966,
    "inference_latency_ms": 2341,
    "created_at": "2026-05-03T10:01:30",
    "alert": null,
    "advisory": null
  }
]
```

If a dangerous state was detected:

```json
{
  "hive_state": "swarming",
  "confidence_score": 0.983,
  "alert": {
    "alert_id": "c3d4e5f6-...",
    "severity_level": "High",
    "recommended_action": "Immediate hive inspection required",
    "action_status": "pending",
    "generated_at": "2026-05-03T10:01:31"
  },
  "advisory": {
    "advisory_id": "d4e5f6a7-...",
    "advisory_type": "Reactive",
    "actions": [
      { "action_description": "Inspect the hive immediately", "priority_level": "High" },
      { "action_description": "Prepare a swarm trap nearby", "priority_level": "High" },
      { "action_description": "Remove swarm cells", "priority_level": "Medium" }
    ]
  }
}
```

Get only the most recent result:

```bash
curl -s http://localhost:8000/hives/1/inferences/latest \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

### Step 8 — View and acknowledge alerts

```bash
# Pending alerts only (default)
curl -s http://localhost:8000/hives/1/alerts \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# All alerts including already acknowledged ones
curl -s "http://localhost:8000/hives/1/alerts?only_pending=false" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

When the farmer has acted on an alert (inspected the hive, added a swarm trap, etc.):

```bash
ALERT_ID="paste-the-alert_id-here"

curl -s -X PATCH http://localhost:8000/hives/1/alerts/$ALERT_ID/acknowledge \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected response:

```json
{
  "alert_id": "c3d4e5f6-...",
  "action_status": "acknowledged"
}
```

---

### Step 9 — Test manual audio upload (alternative path)

You can also upload a wav file directly without SSH, which is useful for quick testing:

```bash
curl -s -X POST http://localhost:8000/audio/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/your/recording.wav" \
  -F "hive_id=1" | python3 -m json.tool
```

Response is immediate (HTTP 202). Inference runs in the background — poll `/hives/1/inferences/latest` after a few seconds.

---

## What Happens Inside — The Full Processing Chain

When the poller or upload picks up a new file, this is the exact sequence:

```
1. download_new_files() — paramiko SFTP downloads file to:
       downloads/{user_id}/{hive_id}/filename.wav

2. process_audio_file(audio_id, file_path, hive_id) is called:

   a. librosa.load(file_path, sr=22050)
      → loads audio, resamples to 22050 Hz

   b. y = y[:5 * 22050]
      → takes first 5 seconds only (matching training segment length)

   c. _extract_features(y, sr) → 171 features:
      - 40 MFCCs × (mean + std)          = 80
      - 40 delta-MFCCs × mean            = 40
      - 12 Chroma × (mean + std)         = 24
      - Mel spectrogram stats            =  4
      - Spectral centroid (mean + std)   =  2
      - Spectral bandwidth (mean + std)  =  2
      - Spectral rolloff (mean + std)    =  2
      - Spectral contrast × 7            =  7
      - Zero crossing rate (mean + std)  =  2
      - RMS energy (mean + std)          =  2
      - Tonnetz × 6                      =  6
                                   Total = 171

   d. gradient_boosting_model.predict(feature_vector)
      → class index

   e. label_encoder.classes_[index]
      → e.g. "active_colony"

   f. Saves FeatureVector row (mfcc_json + summary features)

   g. Saves InferenceResult row (hive_state + confidence + latency)

   h. advisory.generate() — if swarming or missing_queen:
      → creates Alert row
      → creates Advisory row
      → creates AdvisoryAction rows (prioritised checklist)

   i. Updates AudioSource.status = "processed"
      (or "failed" if any step raises an exception)
```

---

## Adding More Audio Files to the Simulation

To add new recordings to the Docker container for the poller to pick up:

```bash
# Copy a wav file into the Docker container
docker cp /path/to/new_recording.wav farmer-sim:/home/farmer/recordings/

# Or generate a silent test file (if sox is available on host)
sox -n -r 44100 -c 1 /tmp/test.wav trim 0.0 5.0
docker cp /tmp/test.wav farmer-sim:/home/farmer/recordings/new_test.wav
```

The poller picks it up within 30 seconds.

---

## Checking the Database Directly

If you want to inspect what was stored in PostgreSQL:

```bash
psql -U bee_user -d bee_db
```

```sql
-- See all inference results
SELECT hive_id, hive_state, confidence_score, created_at
FROM inference_results
ORDER BY created_at DESC;

-- See all alerts
SELECT hive_id, severity_level, action_status, generated_at
FROM alerts;

-- See audio source processing status
SELECT hive_id, source_url, status, ingestion_time_stamp
FROM audio_sources
ORDER BY ingestion_time_stamp DESC;

-- See configured data sources
SELECT hive_id, source_type, source_path, last_scanned_at
FROM farmer_data_sources;
```

---

## Useful Aliases for Testing

Add these to your shell session to save typing:

```bash
BASE="http://localhost:8000"

# After setting TOKEN:
alias hive-results="curl -s $BASE/hives/1/inferences -H \"Authorization: Bearer \$TOKEN\" | python3 -m json.tool"
alias hive-latest="curl -s $BASE/hives/1/inferences/latest -H \"Authorization: Bearer \$TOKEN\" | python3 -m json.tool"
alias hive-alerts="curl -s $BASE/hives/1/alerts -H \"Authorization: Bearer \$TOKEN\" | python3 -m json.tool"
alias hive-source="curl -s $BASE/hives/1/data-source -H \"Authorization: Bearer \$TOKEN\" | python3 -m json.tool"
```
