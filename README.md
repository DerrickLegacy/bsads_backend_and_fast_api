# Bee Swarming & Abscondment Detection System (BSADS)

Classifies beehive audio recordings into 5 states and alerts farmers in real time.

| State | Meaning | Alert? |
|---|---|---|
| `active_colony` | Healthy, normal activity | No |
| `queenbee_present` | Queen detected | No |
| `swarming` | Swarm event in progress | **Yes — High** |
| `missing_queen` | Queen is absent | **Yes — Medium** |
| `external_noise` | Background noise | No |

---

## Quick Start

### 1. Install dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
Edit `.env`:
```
DATABASE_URL=postgresql://bee_user:bee_user@localhost:5432/bee_db
SECRET_KEY=change-this-in-production
UPLOAD_DIR=uploads
```

### 3. Start the server
```bash
uvicorn api.main:app --reload --port 8000
```

On first run, all database tables are created automatically.

### 4. Open interactive docs
```
http://localhost:8000/docs    ← Swagger UI (try endpoints interactively)
http://localhost:8000/redoc   ← ReDoc (clean readable reference)
```

---

## API Usage — Step by Step

### Step 1 — Register a farmer account

```bash
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "fullname": "Derrick Ahaabwe",
    "email": "derrick@bees.ug",
    "password": "mypassword123",
    "telephone_number": "+256700000000",
    "role": "farmer"
  }' | python3 -m json.tool
```

Response:
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "user_id": 1,
    "fullname": "Derrick Ahaabwe",
    "email": "derrick@bees.ug",
    "role": "farmer",
    "created_at": "2026-04-29T13:10:01"
  }
}
```

**Save the `access_token`** — you need it for every other request.

---

### Step 2 — Login (use this if you already have an account)

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "derrick@bees.ug", "password": "mypassword123"}' \
  | python3 -m json.tool
```

---

### Step 3 — Register a hive

```bash
TOKEN="paste_your_token_here"

curl -s -X POST http://localhost:8000/hives \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hive_location": "Kampala, Nakawa",
    "hive_type": "Langstroth",
    "installation_date": "2026-01-15T00:00:00"
  }' | python3 -m json.tool
```

Response:
```json
{
  "hive_id": 1,
  "user_id": 1,
  "hive_location": "Kampala, Nakawa",
  "hive_type": "Langstroth",
  "current_state": "unknown"
}
```

This also creates a watched folder automatically:
```
data_sources/1/1/     ← drop .wav files here (user_id=1, hive_id=1)
```

---

### Step 4a — Upload audio manually

```bash
curl -s -X POST http://localhost:8000/audio/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/hive_recording.wav" \
  -F "hive_id=1" | python3 -m json.tool
```

Response (immediate — inference runs in background):
```json
{
  "audio_id": "3f4a1b2c-...",
  "hive_id": 1,
  "message": "File received. Inference is running in the background."
}
```

---

### Step 4b — Drop files into the watched folder (alternative)

Instead of uploading, simply copy audio files into the hive's folder:

```bash
cp /path/to/recording.wav data_sources/1/1/
```

The poller checks every 30 seconds and processes any new files automatically.
Check the data source status:

```bash
curl -s http://localhost:8000/hives/1/data-source \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

### Step 5 — Get the inference result

Wait 3–5 seconds after upload, then:

```bash
# Latest result only
curl -s http://localhost:8000/hives/1/inferences/latest \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# All results (last 20)
curl -s http://localhost:8000/hives/1/inferences \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Normal hive response:
```json
{
  "inference_id": "a1b2c3...",
  "hive_id": 1,
  "hive_state": "active_colony",
  "confidence_score": 0.9966,
  "inference_latency_ms": 2341,
  "created_at": "2026-04-29T13:15:00",
  "alert": null,
  "advisory": null
}
```

Swarming detected:
```json
{
  "hive_state": "swarming",
  "confidence_score": 0.983,
  "alert": {
    "severity_level": "High",
    "recommended_action": "Immediate hive inspection required",
    "action_status": "pending"
  },
  "advisory": {
    "advisory_type": "Reactive",
    "actions": [
      { "action_description": "Inspect the hive immediately", "priority_level": "High" },
      { "action_description": "Prepare a swarm trap nearby", "priority_level": "High" },
      { "action_description": "Remove swarm cells", "priority_level": "Medium" }
    ]
  }
}
```

---

### Step 6 — View and acknowledge alerts

```bash
# Pending alerts for a hive
curl -s http://localhost:8000/hives/1/alerts \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# All alerts including acknowledged
curl -s "http://localhost:8000/hives/1/alerts?only_pending=false" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Acknowledge an alert (farmer has acted on it)
curl -s -X PATCH http://localhost:8000/hives/1/alerts/<alert_id>/acknowledge \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## All Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Health check |
| GET | `/docs` | No | Swagger UI (interactive) |
| GET | `/redoc` | No | ReDoc reference |
| POST | `/auth/register` | No | Create farmer account |
| POST | `/auth/login` | No | Login, get token |
| GET | `/auth/me` | Yes | My profile |
| POST | `/hives` | Yes | Register hive |
| GET | `/hives` | Yes | List my hives |
| GET | `/hives/{id}` | Yes | Get one hive |
| GET | `/hives/{id}/data-source` | Yes | Data source folder info |
| POST | `/audio/upload` | Yes | Upload audio file |
| GET | `/hives/{id}/inferences` | Yes | All results (last 20) |
| GET | `/hives/{id}/inferences/latest` | Yes | Most recent result |
| GET | `/hives/{id}/alerts` | Yes | Pending alerts |
| PATCH | `/hives/{id}/alerts/{alert_id}/acknowledge` | Yes | Acknowledge alert |

---

## Tip — pretty-print all curl responses

Add `| python3 -m json.tool` to the end of any curl command:
```bash
curl -s http://localhost:8000/ | python3 -m json.tool
```

Or install `jq` for coloured output:
```bash
sudo apt install jq
curl -s http://localhost:8000/ | jq
```
