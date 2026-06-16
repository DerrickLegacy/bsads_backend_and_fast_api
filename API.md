# BSADS FastAPI — Deep Dive Documentation

**Bee Swarming & Abscondment Detection System — Backend Service**

---

## Table of Contents

1. [What This API Does](#1-what-this-api-does)
2. [How the System Flows End-to-End](#2-how-the-system-flows-end-to-end)
3. [The Database — Tables and Relationships](#3-the-database--tables-and-relationships)
4. [Authentication — How JWT Works](#4-authentication--how-jwt-works)
5. [The Inference Pipeline — Deep Insight](#5-the-inference-pipeline--deep-insight)
6. [Advisory Generation — The Rules Engine](#6-advisory-generation--the-rules-engine)
7. [All Endpoints Reference](#7-all-endpoints-reference)
8. [How to Set Up and Run Locally](#8-how-to-set-up-and-run-locally)
9. [Testing Every Endpoint (Step-by-Step)](#9-testing-every-endpoint-step-by-step)
10. [How the Mobile App Connects](#10-how-the-mobile-app-connects)
11. [Project File Structure Explained](#11-project-file-structure-explained)

---

## 1. What This API Does

The BSADS API sits between two worlds:

- **Farmers** — who have beehives with audio sensors
- **A trained ML model** — that can classify what is happening in a hive from audio

The API receives an audio recording, sends it through the ML pipeline, and tells the farmer what state their hive is in. There are five possible states:

| State              | Meaning                                    |
| ------------------ | ------------------------------------------ |
| `active_colony`    | Hive is healthy and active — normal        |
| `queenbee_present` | Queen is detected — normal                 |
| `swarming`         | Bees are swarming — **urgent alert**       |
| `missing_queen`    | Queen is absent — **alert**                |
| `external_noise`   | Background noise detected — low confidence |

When a dangerous state is detected, the API automatically creates an **Alert** and an **Advisory** — a prioritised checklist of actions the farmer should take.

---

## 2. How the System Flows End-to-End

Understanding this flow is the most important thing. Read it carefully.

```
FARMER'S DEVICE
      │
      │  POST /audio/upload
      │  (sends .wav file + hive_id)
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI receives the file           │
│                                                     │
│  1. Checks: does this hive belong to this farmer?  │
│  2. Saves the .wav to: uploads/{user}/{hive}/file  │
│  3. Creates an audio_source row (status=pending)   │
│  4. Returns HTTP 202 immediately ◄─── farmer gets  │
│     { audio_id, message: "processing..." }          │
│                                                     │
│  5. Launches a BACKGROUND TASK (runs separately):  │
│     ┌───────────────────────────────────────────┐  │
│     │  a. Load .wav with librosa                │  │
│     │  b. Extract 171 acoustic features         │  │
│     │  c. Save feature_vector row               │  │
│     │  d. Run Gradient Boosting model           │  │
│     │  e. Save inference_result row             │  │
│     │  f. If swarming/missing_queen:            │  │
│     │     → Create Alert row                    │  │
│     │     → Create Advisory row                 │  │
│     │     → Create 5 AdvisoryAction rows        │  │
│     │  g. Update audio_source status=processed  │  │
│     └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
      │
      │  Later, mobile app polls:
      │  GET /hives/{hive_id}/inferences/latest
      │
      ▼
FARMER SEES RESULT
  { hive_state: "swarming", confidence: 0.983, alert: {...} }
```

**Why HTTP 202 instead of waiting?**

Feature extraction takes 2–5 seconds (librosa processes the audio). If the API made the farmer wait, the mobile app would time out or feel slow. By returning immediately and processing in the background, the upload feels instant. The mobile app then polls for the result.

---

## 3. The Database — Tables and Relationships

All tables are created automatically in `bee_db` when the app starts. Here is how they connect:

```
users ──────────────────────────────────────────────────────────────┐
  │ user_id (PK)                                                    │
  │                                                                 │
  ▼ (one user → many hives)                                         │
hives ──────────────────────────────────────────────────────────────┤
  │ hive_id (PK), user_id (FK)                                      │
  │                                                                 │
  ├──► audio_sources                                                │
  │      audio_id (PK), hive_id (FK)                               │
  │      source_url — where the .wav is stored                     │
  │      status — pending | processing | processed | failed         │
  │           │                                                     │
  │           ▼                                                     │
  │    feature_vectors                                              │
  │      feature_id (PK), audio_id (FK), hive_id (FK)              │
  │      mfcc_value (JSON), spectral_centroid, ...                  │
  │           │                                                     │
  │           ▼                                                     │
  ├──► inference_results ◄──────────────────────────────────────────┤
  │      inference_id (PK), feature_id (FK), hive_id (FK)          │
  │      hive_state, confidence_score, inference_latency_ms         │
  │           │                                                     │
  │           ├──► alerts                                          │
  │           │      alert_id, hive_id (FK), inference_id (FK)     │
  │           │      severity_level, action_status                  │
  │           │                                                     │
  │           └──► advisories                                      │
  │                  advisory_id, inference_id (FK), hive_id (FK)  │
  │                       │                                        │
  │                       └──► advisory_actions                    │
  │                              action_id, advisory_id (FK)       │
  │                              action_description, priority_level │
  │                                                                 │
  ├──► environmental_data (optional — temperature/humidity)         │
  └──► image_spectra (optional — spectrogram images)               │
```

**Key design insight:** Every piece of data is scoped to a `hive_id`, which is owned by a `user_id`. This means every query the mobile app makes is filtered by the logged-in farmer's user ID — a farmer can never see another farmer's data.

---

## 4. Authentication — How JWT Works

The API uses **JWT (JSON Web Tokens)**. Here is exactly what happens:

### Registration / Login

```
Farmer registers → password is hashed with bcrypt (never stored plain)
                → JWT token is generated containing { user_id, expiry }
                → Token is returned to the mobile app
```

### Every subsequent request

```
Mobile app sends:   Authorization: Bearer <token>
API decodes token:  → extracts user_id
                    → loads user from database
                    → attaches user to the request
Any endpoint with   Depends(get_current_user) automatically does this
```

### Why this matters for you as a developer

When you test an endpoint that requires login, you must:

1. Call `/auth/login` first → get the token
2. Copy the token
3. Add it as a header: `Authorization: Bearer <your_token>` on every protected request

The interactive docs at `/docs` handle this for you with the **Authorize** button.

---

## 5. The Inference Pipeline — Deep Insight

This is the heart of the system. Understanding this helps you debug problems.

### Step 1 — Audio loading

```python
y, sr = librosa.load(file_path, sr=22050)
y = y[:int(5.0 * sr)]   # first 5 seconds only
```

Why 22050 Hz? That is the same sample rate used during training. If you load at a different rate, the features will be different and the model will give wrong results.

Why 5 seconds? The training data used 5-second segments. The model learned from 5-second windows.

### Step 2 — Feature extraction (171 features)

| Feature Group         | Count   | What it captures                       |
| --------------------- | ------- | -------------------------------------- |
| MFCCs (mean + std)    | 80      | Timbre — the "colour" of the sound     |
| Delta MFCCs (mean)    | 40      | How MFCCs change over time             |
| Chroma (mean + std)   | 24      | Pitch class content                    |
| Mel spectrogram stats | 4       | Energy distribution across frequencies |
| Spectral centroid     | 2       | Brightness of sound                    |
| Spectral bandwidth    | 2       | Spread of frequencies                  |
| Spectral rolloff      | 2       | High-frequency content                 |
| Spectral contrast     | 7       | Peak vs valley in spectrum             |
| Zero crossing rate    | 2       | Signal noisiness                       |
| RMS energy            | 2       | Loudness                               |
| Tonnetz               | 6       | Harmonic content                       |
| **Total**             | **171** |                                        |

### Step 3 — Model prediction

```python
class_index = model.predict(vector)[0]       # which class (0-4)
probabilities = model.predict_proba(vector)[0] # confidence per class
confidence = probabilities[class_index]       # confidence of the chosen class
```

`predict_proba` gives you the probability for EACH class. The highest one wins. If the winning probability is low (e.g., 0.45), the model is uncertain — this is worth logging.

### Step 4 — Latency measurement

```python
t0 = time.perf_counter()
# ... model inference ...
latency_ms = int((time.perf_counter() - t0) * 1000)
```

Latency is stored in `inference_results.inference_latency_ms`. Typical values:

- Feature extraction: 1,000–3,000 ms (librosa is the slow part)
- Model prediction: 5–50 ms (Gradient Boosting is fast)

---

## 6. Advisory Generation — The Rules Engine

`api/advisory.py` contains a simple but effective rules engine. When the model classifies a hive as `swarming` or `missing_queen`, it fires:

```python
_RULES = {
    "swarming": {
        "severity_level": "High",
        "advisory_type": "Reactive",
        "actions": [
            ("Inspect the hive immediately...", "High"),
            ("Prepare a swarm trap...", "High"),
            ("Remove swarm cells...", "Medium"),
            ("Ensure adequate space...", "Medium"),
            ("Contact a local beekeeper...", "Low"),
        ]
    },
    "missing_queen": { ... }
}
```

**Why a rules engine and not another model?**

The advisory recommendations are domain knowledge — they come from beekeeping expertise, not from the audio data. A rules engine is transparent, easy to update, and explainable to a farmer. You can add new rules simply by editing the dictionary.

**To add a new rule** (e.g., for `external_noise`), add a key to `_RULES` in `api/advisory.py` and restart the server.

---

## 7. All Endpoints Reference

Base URL (local): `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`
BAse URL (railway):`https://bsads-api-production.up.railway.app/docs`

### Authentication

| Method | Endpoint         | Auth required | Description              |
| ------ | ---------------- | ------------- | ------------------------ |
| POST   | `/auth/register` | No            | Create a farmer account  |
| POST   | `/auth/login`    | No            | Login, receive JWT token |
| GET    | `/auth/me`       | Yes           | Get current user profile |

### Hives

| Method | Endpoint           | Auth required | Description         |
| ------ | ------------------ | ------------- | ------------------- |
| POST   | `/hives`           | Yes           | Register a new hive |
| GET    | `/hives`           | Yes           | List all my hives   |
| GET    | `/hives/{hive_id}` | Yes           | Get one hive        |

### Audio Upload

| Method | Endpoint        | Auth required | Description                     |
| ------ | --------------- | ------------- | ------------------------------- |
| POST   | `/audio/upload` | Yes           | Upload audio, trigger inference |

### Inference Results (mobile reads here)

| Method | Endpoint                             | Auth required | Description                |
| ------ | ------------------------------------ | ------------- | -------------------------- |
| GET    | `/hives/{hive_id}/inferences`        | Yes           | Last 20 results for a hive |
| GET    | `/hives/{hive_id}/inferences/latest` | Yes           | Most recent result only    |

### Alerts

| Method | Endpoint                                         | Auth required | Description                       |
| ------ | ------------------------------------------------ | ------------- | --------------------------------- |
| GET    | `/hives/{hive_id}/alerts`                        | Yes           | Pending alerts for a hive         |
| GET    | `/hives/{hive_id}/alerts?only_pending=false`     | Yes           | All alerts including acknowledged |
| PATCH  | `/hives/{hive_id}/alerts/{alert_id}/acknowledge` | Yes           | Mark alert as seen                |

### Mobile Alerts (Top-level endpoints for mobile app)

| Method | Endpoint                         | Auth required | Description                                            |
| ------ | -------------------------------- | ------------- | ------------------------------------------------------ |
| GET    | `/alerts`                        | Yes           | List all alerts for current user's hives               |
| GET    | `/alerts?hive_id={hive_id}`      | Yes           | Filter alerts by specific hive                         |
| GET    | `/alerts/{alert_id}`             | Yes           | Get alert detail with audio recording and actions ⭐   |
| GET    | `/alerts/{alert_id}/advisory`    | Yes           | Get just the advisory actions for an alert             |
| POST   | `/alerts/{alert_id}/acknowledge` | Yes           | Mark alert as acknowledged                             |

### Health Check

| Method | Endpoint | Auth required | Description      |
| ------ | -------- | ------------- | ---------------- |
| GET    | `/`      | No            | API status check |

---

## 8. How to Set Up and Run Locally

### Prerequisites

- Python 3.11+
- PostgreSQL running with `bee_db`, user `bee_user`, password `bee_user`
- The trained model files in `models/`

### 1. Clone and set up environment

```bash
git clone git@github.com:DerrickLegacy/bee_swarming_and_absconment_audio_classifer.git
cd bee_swarming_and_absconment_audio_classifer

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure the database

```bash
# In psql as the postgres superuser:
psql -U postgres
CREATE DATABASE bee_db;
CREATE USER bee_user WITH PASSWORD 'bee_user';
GRANT ALL PRIVILEGES ON DATABASE bee_db TO bee_user;
\q
```

### 3. Check your .env file

```
DATABASE_URL=postgresql://bee_user:bee_user@localhost:5432/bee_db
SECRET_KEY=bee-swarming-system-secret-key-change-in-production
UPLOAD_DIR=uploads
HF_TOKEN=<your_huggingface_token>
```

### 4. Start the server

```bash
uvicorn api.main:app --reload --port 8000
```

On first start you will see:

```
✓ Database tables ready
✓ Upload directory ready
✓ Model loaded: models/gradient_boosting_model.pkl
INFO:     Uvicorn running on http://0.0.0.0:8000
```

All 10 database tables are created automatically.

---

## 9. Testing Every Endpoint (Step-by-Step)

Open `http://localhost:8000/docs` in your browser for an interactive version.
Or use these `curl` commands in your terminal.

### Step 1 — Register a farmer account

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "fullname": "Derrick Ahaabwe",
    "email": "derrick@bees.ug",
    "password": "mypassword123",
    "telephone_number": "+256700000000",
    "role": "farmer"
  }'
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "user_id": 1,
    "fullname": "Derrick Ahaabwe",
    "email": "derrick@bees.ug",
    "role": "farmer",
    "created_at": "2026-04-29T10:00:00"
  }
}
```

Save the `access_token` — you need it for all other requests.

---

### Step 2 — Login (if you already have an account)

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "derrick@bees.ug", "password": "mypassword123"}'
```

---

### Step 3 — Register a hive

```bash
curl -X POST http://localhost:8000/hives \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "hive_location": "Kampala, Nakawa",
    "hive_type": "Langstroth",
    "installation_date": "2026-01-15T00:00:00"
  }'
```

**Response:**

```json
{
  "hive_id": 1,
  "user_id": 1,
  "hive_location": "Kampala, Nakawa",
  "hive_type": "Langstroth",
  "installation_date": "2026-01-15T00:00:00",
  "current_state": "unknown"
}
```

---

### Step 4 — Upload a hive audio recording

```bash
curl -X POST http://localhost:8000/audio/upload \
  -H "Authorization: Bearer <your_token>" \
  -F "file=@/path/to/your/hive_recording.wav" \
  -F "hive_id=1"
```

**Response (immediate — 202 Accepted):**

```json
{
  "audio_id": "3f4a1b2c-...",
  "hive_id": 1,
  "message": "File receivegit ad. Inference is running in the background."
}
```

The model is now running in the background. Wait 3–5 seconds then check results.

---

### Step 5 — Get the inference result

```bash
curl http://localhost:8000/hives/1/inferences/latest \
  -H "Authorization: Bearer <your_token>"
```

**Response (normal hive):**

```json
{
  "inference_id": "a1b2c3d4-...",
  "hive_id": 1,
  "hive_state": "active_colony",
  "confidence_score": 0.9966,
  "inference_latency_ms": 2341,
  "created_at": "2026-04-29T10:05:23",
  "alert": null,
  "advisory": null
}
```

**Response (swarming detected):**

```json
{
  "inference_id": "a1b2c3d4-...",
  "hive_id": 1,
  "hive_state": "swarming",
  "confidence_score": 0.983,
  "inference_latency_ms": 2105,
  "created_at": "2026-04-29T10:05:23",
  "alert": {
    "alert_id": "x1y2z3-...",
    "hive_id": 1,
    "severity_level": "High",
    "recommended_action": "Immediate hive inspection required — swarm event detected",
    "action_status": "pending",
    "generated_at": "2026-04-29T10:05:24"
  },
  "advisory": {
    "advisory_id": "p1q2r3-...",
    "advisory_type": "Reactive",
    "actions": [
      {
        "action_description": "Inspect the hive immediately to confirm swarming activity",
        "priority_level": "High",
        "status": "pending"
      },
      {
        "action_description": "Prepare a swarm trap or empty hive box nearby to capture the swarm",
        "priority_level": "High",
        "status": "pending"
      },
      {
        "action_description": "Remove or destroy swarm cells to prevent secondary swarms",
        "priority_level": "Medium",
        "status": "pending"
      },
      {
        "action_description": "Ensure the hive has enough space to reduce overcrowding",
        "priority_level": "Medium",
        "status": "pending"
      },
      {
        "action_description": "Contact a local beekeeper association for immediate assistance",
        "priority_level": "Low",
        "status": "pending"
      }
    ]
  }
}
```

---

### Step 6 — View and acknowledge an alert

```bash
# View all alerts for current user
curl http://localhost:8000/alerts \
  -H "Authorization: Bearer <your_token>"

# View alerts for a specific hive
curl http://localhost:8000/alerts?hive_id=1 \
  -H "Authorization: Bearer <your_token>"

# Get detailed information about a specific alert (includes audio file path)
curl http://localhost:8000/alerts/<alert_id> \
  -H "Authorization: Bearer <your_token>"
```

**Response with audio traceability:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "hive_id": "123e4567-e89b-12d3-a456-426614174000",
  "hive_name": "Hive A - Apiary 1",
  "severity": "critical",
  "title": "Swarm Detected",
  "time": "2026-06-09T10:30:00",
  "created_at": "2026-06-09T10:30:00",
  "details": "Active swarm event detected - immediate intervention required",
  "acknowledged": false,
  
  "audio_recording": {
    "id": "789e0123-e89b-12d3-a456-426614174111",
    "file_path": "/path/to/farmer/hive/recordings/2026-06-09_10-30-00.wav",
    "duration_seconds": 30,
    "recorded_at": "2026-06-09T10:30:00"
  },
  
  "advisory": {
    "id": "advisory-uuid",
    "alert_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "Reactive",
    "summary": "Active swarm event detected...",
    "actions": [
      {
        "id": "action-1",
        "description": "Inspect the hive immediately to confirm swarming activity",
        "priority": "High"
      },
      {
        "id": "action-2",
        "description": "Prepare a swarm trap or empty hive box nearby to capture the swarm",
        "priority": "High"
      },
      {
        "id": "action-3",
        "description": "Remove or destroy swarm cells to prevent secondary swarms",
        "priority": "Medium"
      }
    ]
  }
}
```

**Audio Traceability:** The `audio_recording.file_path` field contains the exact location of the audio file that triggered this alert. This allows you to:
- Play the audio in the mobile app
- Download it for further analysis
- Show the farmer which recording caused the alert

```bash
# Acknowledge an alert (farmer has acted on it)
curl -X POST http://localhost:8000/alerts/<alert_id>/acknowledge \
  -H "Authorization: Bearer <your_token>"
```

---

### Step 7 — Legacy hive-scoped alert endpoints

These endpoints are also available for backwards compatibility:

```bash
# View pending alerts for a specific hive
curl http://localhost:8000/hives/1/alerts \
  -H "Authorization: Bearer <your_token>"

# Acknowledge an alert (legacy endpoint)
curl -X PATCH http://localhost:8000/hives/1/alerts/<alert_id>/acknowledge \
  -H "Authorization: Bearer <your_token>"
```

---

## 10. How the Mobile App Connects

Share this information with your mobile development team.

### Base URL

- **Local testing:** `http://localhost:8000`
- **After deployment to Railway/Render:** the URL they give you (e.g., `https://bsads-api.railway.app`)

### Authentication flow for mobile

```
1. Farmer opens app → calls POST /auth/login
2. App stores the token securely (e.g., in device keychain)
3. Every API call includes: Authorization: Bearer <token>
4. Token lasts 24 hours — after that, call /auth/login again
```

### Recommended mobile polling pattern

```
After farmer uploads audio:
  → Call GET /hives/{id}/inferences/latest every 3 seconds
  → When hive_state is no longer null, show the result
  → If alert is not null, show a notification to the farmer
```

### CORS

The API allows requests from any origin (`*`). In production this should be tightened to only allow the mobile app's domain.

---

## 11. Project File Structure Explained

```
bee_swarming_audio_classifer/
│
├── api/                          ← The FastAPI service
│   ├── config.py                 ← Reads .env — all settings in one place
│   ├── database.py               ← SQLAlchemy connection to bee_db
│   ├── models.py                 ← 10 database tables as Python classes
│   ├── schemas.py                ← Pydantic — what the API sends/receives
│   ├── inference_engine.py       ← Loads .pkl, extracts features, predicts
│   ├── advisory.py               ← Rules: "swarming" → what actions to create
│   ├── main.py                   ← FastAPI app, registers all routers
│   ├── requirements.txt          ← API-only dependencies (for Docker)
│   └── routers/
│       ├── auth.py               ← /auth/register, /auth/login
│       ├── hives.py              ← /hives (CRUD)
│       ├── audio.py              ← /audio/upload (the main endpoint)
│       ├── inferences.py         ← /hives/{id}/inferences (mobile reads here)
│       └── alerts.py             ← /hives/{id}/alerts (mobile reads here)
│
├── models/                       ← Trained .pkl model files
│   ├── gradient_boosting_model.pkl   ← Best model (used for inference)
│   ├── label_encoder.pkl             ← Maps number → class name
│   └── ...
│
├── notebooks/                    ← Jupyter notebooks (training pipeline)
├── features/                     ← Pipeline outputs (CSVs, plots)
├── scripts/
│   └── deploy_to_huggingface.py  ← Pushes models to Hugging Face
│
├── uploads/                      ← Audio files uploaded by farmers at runtime
│   └── {user_id}/{hive_id}/     ← Organised per farmer per hive
│
├── Dockerfile                    ← For deploying to Railway or Render
├── requirements.txt              ← ALL dependencies (ML + API combined)
└── .env                          ← Secrets — never committed to git
```

---

## Quick Reference Card

```
Start API          uvicorn api.main:app --reload --port 8000
Interactive docs   http://localhost:8000/docs
Health check       GET  /
Register           POST /auth/register
Login              POST /auth/login
Add hive           POST /hives
Upload audio       POST /audio/upload   (multipart: file + hive_id)
See results        GET  /hives/{id}/inferences/latest
See all results    GET  /hives/{id}/inferences
See alerts         GET  /hives/{id}/alerts
Acknowledge alert  PATCH /hives/{id}/alerts/{alert_id}/acknowledge
```
