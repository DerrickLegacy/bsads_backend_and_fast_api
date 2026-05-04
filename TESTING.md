# BSADS FastAPI — Testing Guide

Full walkthrough of the 7-step inference pipeline using curl commands.

---

## Prerequisites

1. **API is running**

   ```bash
   source venv/bin/activate
   uvicorn api.main:app --reload --port 8000
   ```

2. **Farmer SSH simulation is running** (for the SSH path — Steps 4-6 of the pipeline)

   The simulation is a Docker container that acts as a farmer's external server with audio files
   ready in `/home/farmer/recordings/`.

   ```bash
   # Check if it is already running
   docker ps | grep farmer-sim

   # If not, start it (adjust the path to where you have the simulation project)
   cd /path/to/bsads_farmer_external_data_source_simulation
   docker compose up -d
   docker compose ps    # farmer-sim should show "Up"
   ```

   SSH connection details for the simulation:
   ```
   host: 127.0.0.1 (localhost)
   port: 2222
   username: farmer
   password: farmerpass123
   remote_folder: /home/farmer/recordings
   ```

3. **Verify the SSH server is reachable and folder structure is in place**

   ```bash
   python3 -c "
   import paramiko
   c = paramiko.SSHClient()
   c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
   c.connect('127.0.0.1', port=2222, username='farmer', password='farmerpass123')
   sftp = c.open_sftp()
   print('Top-level:', sftp.listdir('/home/farmer/recordings'))
   print('farmer_1/hive_1:', sftp.listdir('/home/farmer/recordings/farmer_1/hive_1'))
   c.close()
   "
   # Expected:
   # Top-level: ['farmer_1', 'farmer_2', ...]
   # farmer_1/hive_1: ['hive1_morning.wav', 'hive1_afternoon.wav', ...]
   ```

   If the subfolders don't exist yet, create them first (see "Adding More Audio Files" below).


---

## The 7-Step Pipeline — What We Are Testing

```
Step 1:  Sensor audio files exist on the farmer's external server
Step 2:  FastAPI discovery job polls the server via SSH/SFTP
Step 3:  File paths are registered in DB with status=pending
Step 4:  FastAPI inference job fetches audio bytes + sends to HuggingFace Space
Step 5:  HuggingFace Gradio Space returns classification result
Step 6:  Result is stored in DB (InferenceResult + optional Alert/Advisory)
Step 7:  Mobile app (or curl) reads results from the API
```

The curl commands below walk through each step and let you observe the state at every stage.

---

## Part 1 — Account Setup (one time)

### Register a farmer account

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

Expected:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "user_id": 1,
    "fullname": "Test Farmer",
    "email": "farmer@test.ug",
    "role": "farmer"
  }
}
```

Export the token so the next commands pick it up automatically:

```bash
export TOKEN=$(curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"fullname":"Test Farmer","email":"farmer@test.ug","password":"pass1234","role":"farmer"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: ${TOKEN:0:40}..."
```

### Login (if you already registered)

```bash
export TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"farmer@test.ug","password":"pass1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: ${TOKEN:0:40}..."
```

### Check your profile

```bash
curl -s http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Part 2 — Register a Hive

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

Expected:

```json
{
  "hive_id": 1,
  "user_id": 1,
  "hive_location": "Kampala, Nakawa Lab",
  "hive_type": "Langstroth",
  "installation_date": "2026-01-15T00:00:00",
  "current_state": "unknown",
  "suggested_remote_folder": "farmer_1/hive_1"
}
```

`suggested_remote_folder` is the path the farmer should create on their external server
and point their audio sensor to. It follows the convention `farmer_{user_id}/hive_{hive_id}/`.
On the simulation server the full path would be:
`/home/farmer/recordings/farmer_1/hive_1/`

This also auto-creates a local watched folder at `data_sources/1/1/` and registers a
`FarmerDataSource` record. The next step upgrades it to SSH.

---

## Part 3 — Configure SSH Data Source (Step 1 setup)

Tell the API where the farmer's external server is. This is what makes Step 1 of the pipeline
real: from this point on, the poller will connect to that server every 30 seconds.

`remote_folder` follows the convention `farmer_{user_id}/hive_{hive_id}` — use the
`suggested_remote_folder` value returned when you registered the hive.

```bash
curl -s -X POST http://localhost:8000/hives/1/data-source/configure \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_host": "127.0.0.1",
    "ssh_port": 2222,
    "ssh_username": "farmer",
    "ssh_password": "farmerpass123",
    "remote_folder": "/home/farmer/recordings/farmer_1/hive_1"
  }' | python3 -m json.tool
```

Expected — the API immediately tests the connection and tells you if it worked:

```json
{
  "source_id": "a1b2c3d4-...",
  "hive_id": 1,
  "source_type": "ssh",
  "remote_folder": "/home/farmer/recordings/farmer_1/hive_1",
  "connection_test": {
    "ok": true
  }
}
```

If `connection_test.ok` is `false` the `error` field explains what went wrong. The config is
saved either way so you can fix credentials and reconfigure without re-entering everything.

---

## Step 2 — FastAPI Polls the External Server

The discovery poller runs automatically every 30 seconds. No curl command needed here —
just watch the API server terminal output. Within 30 seconds of configuring the SSH source
you should see:

```
[POLLER/ssh] hive=1 registered pending → /home/farmer/recordings/farmer_1/hive_1/hive1_morning.wav
[POLLER/ssh] hive=1 registered pending → /home/farmer/recordings/farmer_1/hive_1/hive1_afternoon.wav
```

---

## Step 3 — File Paths Stored in DB as Pending

Verify the pending rows were created. Check the data source was scanned:

```bash
curl -s http://localhost:8000/hives/1/data-source \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected — `last_scanned_at` now has a timestamp:

```json
{
  "source_id": "a1b2c3d4-...",
  "hive_id": 1,
  "source_type": "ssh",
  "source_path": "/home/farmer/recordings",
  "last_scanned_at": "2026-05-04T10:01:00",
  "is_active": true
}
```

You can also check the DB directly:

```bash
psql -U bee_user -d bee_db -c "
SELECT audio_id, source_url, status, ingestion_time_stamp
FROM audio_sources
WHERE hive_id = 1
ORDER BY ingestion_time_stamp DESC;"
```

```
 audio_id | source_url                                                          | status  | ingestion_time_stamp
----------+---------------------------------------------------------------------+---------+---------------------
 <uuid>   | /home/farmer/recordings/farmer_1/hive_1/hive1_morning.wav           | pending | 2026-05-04 10:01:00
 <uuid>   | /home/farmer/recordings/farmer_1/hive_1/hive1_afternoon.wav         | pending | 2026-05-04 10:01:00
```

---

## Step 4 — Bytes Fetched + Sent to HuggingFace

The inference poller runs 10 seconds after the discovery poller. Again, watch the server logs:

```
[INFERENCE] hive=1 audio=<uuid> → active_colony (99.66%) in 2341ms
[INFERENCE] hive=1 audio=<uuid> → active_colony (97.12%) in 1988ms
[INFERENCE] hive=1 audio=<uuid> → swarming (98.30%) in 2105ms
```

Each line means:
- Audio bytes were fetched over SFTP (Step 4)
- Bytes were POSTed to the HuggingFace Gradio Space
- The Space returned a result (Step 5)
- The result was written to the DB (Step 6)

If you see `[ERROR] processing failed for audio …` check that:
- The HuggingFace Space is awake (visit it in a browser to wake the free-tier Space)
- `HF_SPACE_NAME` in `.env` matches your deployed Space name
- `INFERENCE_TIMEOUT_SECONDS` is large enough (default 240 — HF cold start can take ~60s)

---

## Step 5 — Inference Result Returned from HuggingFace

This happens inside the inference poller (no user action needed). The result from the HF Space
is `{ "label": "...", "score": 0.XX, "all_scores": {...} }`.

---

## Step 6 — Result Stored in DB

Verify in the database:

```bash
psql -U bee_user -d bee_db -c "
SELECT hive_id, hive_state, confidence_score, inference_latency_ms, created_at
FROM inference_results
WHERE hive_id = 1
ORDER BY created_at DESC;"
```

```
 hive_id |   hive_state   | confidence_score | inference_latency_ms |       created_at
---------+----------------+------------------+----------------------+-------------------------
       1 | active_colony  |           0.9966 |                 2341 | 2026-05-04 10:01:30
       1 | active_colony  |           0.9712 |                 1988 | 2026-05-04 10:01:32
       1 | swarming       |           0.9830 |                 2105 | 2026-05-04 10:01:34
```

Check alerts created for dangerous states:

```bash
psql -U bee_user -d bee_db -c "
SELECT hive_id, severity_level, action_status, generated_at
FROM alerts
WHERE hive_id = 1;"
```

---

## Step 7 — Mobile App Reads Results

These are the exact endpoints the React Native app calls. Simulate them with curl:

### Get all inference results (last 20)

```bash
curl -s http://localhost:8000/hives/1/inferences \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Sample result for a healthy hive:

```json
[
  {
    "inference_id": "b2c3d4e5-...",
    "hive_id": 1,
    "hive_state": "active_colony",
    "confidence_score": 0.9966,
    "inference_latency_ms": 2341,
    "created_at": "2026-05-04T10:01:30",
    "alert": null,
    "advisory": null
  }
]
```

Sample result when a swarm was detected:

```json
[
  {
    "hive_state": "swarming",
    "confidence_score": 0.983,
    "alert": {
      "alert_id": "c3d4e5f6-...",
      "severity_level": "High",
      "recommended_action": "Immediate hive inspection required",
      "action_status": "pending"
    },
    "advisory": {
      "advisory_type": "Reactive",
      "actions": [
        { "action_description": "Inspect the hive immediately", "priority_level": "High" },
        { "action_description": "Prepare a swarm trap nearby",  "priority_level": "High" },
        { "action_description": "Remove swarm cells",           "priority_level": "Medium" }
      ]
    }
  }
]
```

### Get only the most recent result (what the mobile dashboard shows)

```bash
curl -s http://localhost:8000/hives/1/inferences/latest \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### View pending alerts

```bash
curl -s http://localhost:8000/hives/1/alerts \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Include already-acknowledged alerts
curl -s "http://localhost:8000/hives/1/alerts?only_pending=false" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### Acknowledge an alert (farmer marks it as acted on)

```bash
ALERT_ID="paste-the-alert_id-here"

curl -s -X PATCH http://localhost:8000/hives/1/alerts/$ALERT_ID/acknowledge \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected:

```json
{
  "alert_id": "c3d4e5f6-...",
  "action_status": "acknowledged"
}
```

---

## Alternative: Manual Upload (bypasses the SSH pipeline)

If you want to test inference directly without the SSH simulation, upload a `.wav` file manually.
This enters the pipeline at Step 4 (bytes are sent directly to HuggingFace):

```bash
# Download a short test wav if you don't have one
# sox -n -r 44100 -c 1 /tmp/test.wav trim 0.0 5.0

curl -s -X POST http://localhost:8000/audio/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/your/recording.wav" \
  -F "hive_id=1" | python3 -m json.tool
```

Response is immediate (HTTP 202 Accepted). Inference runs in a background task. Poll the result:

```bash
# Wait ~5–60 seconds for the HF Space to respond, then:
curl -s http://localhost:8000/hives/1/inferences/latest \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Adding More Audio Files to the SSH Simulation

The simulation server organises files by farmer and hive:
`/home/farmer/recordings/farmer_{user_id}/hive_{hive_id}/`

Create the subfolder structure and drop in recordings:

```bash
# Create folders for farmer 1, hive 1 and hive 2 (run once)
docker exec farmer-sim mkdir -p /home/farmer/recordings/farmer_1/hive_1
docker exec farmer-sim mkdir -p /home/farmer/recordings/farmer_1/hive_2
docker exec farmer-sim mkdir -p /home/farmer/recordings/farmer_2/hive_1

# Copy a wav file into the correct hive folder
docker cp /path/to/new_recording.wav farmer-sim:/home/farmer/recordings/farmer_1/hive_1/

# Generate a silent test wav with sox (if installed on your host) and copy it in
sox -n -r 44100 -c 1 /tmp/silent_test.wav trim 0.0 5.0
docker cp /tmp/silent_test.wav farmer-sim:/home/farmer/recordings/farmer_1/hive_1/silent_test.wav
```

The poller picks it up within 30 seconds. Watch the server logs for the `[POLLER/ssh]` lines.

---

## Useful Shell Aliases

Add to your terminal session to save typing during extended testing:

```bash
BASE="http://localhost:8000"
# (TOKEN must already be exported)

alias hive-results="curl -s $BASE/hives/1/inferences     -H \"Authorization: Bearer \$TOKEN\" | python3 -m json.tool"
alias hive-latest="curl -s  $BASE/hives/1/inferences/latest -H \"Authorization: Bearer \$TOKEN\" | python3 -m json.tool"
alias hive-alerts="curl -s  $BASE/hives/1/alerts          -H \"Authorization: Bearer \$TOKEN\" | python3 -m json.tool"
alias hive-source="curl -s  $BASE/hives/1/data-source     -H \"Authorization: Bearer \$TOKEN\" | python3 -m json.tool"
```

---

## Checking the Database Directly

```bash
psql -U bee_user -d bee_db
```

```sql
-- Full pipeline state for all audio in hive 1
SELECT
  a.audio_id,
  a.source_url,
  a.status           AS audio_status,
  i.hive_state,
  i.confidence_score,
  i.inference_latency_ms,
  al.severity_level,
  al.action_status
FROM audio_sources a
LEFT JOIN inference_results i  ON i.hive_id = a.hive_id
LEFT JOIN alerts al            ON al.inference_id = i.inference_id
WHERE a.hive_id = 1
ORDER BY a.ingestion_time_stamp DESC;

-- All pending alerts across all hives
SELECT hive_id, severity_level, action_status, generated_at
FROM alerts
WHERE action_status = 'pending'
ORDER BY generated_at DESC;

-- Configured data sources
SELECT hive_id, source_type, source_path, last_scanned_at, is_active
FROM farmer_data_sources;
```
