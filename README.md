# BSADS — FastAPI Backend Service

**Bee Swarming & Abscondment Detection System**

This is the production API for the BSADS project. It connects farmers' remote audio sensors to a trained ML model hosted on HuggingFace, stores inference results, generates alerts, and serves data to the mobile app.

---

## What This Service Does

Beehive audio sensors record sound continuously. This API:

1. Polls the farmer's external server via HTTP API every 30 seconds for new recordings
2. Registers every new audio file in the database with `status=pending`
3. Fetches the audio bytes and sends them to the HuggingFace Gradio Space for classification
4. Receives the classification result (label + confidence score) from HuggingFace
5. Stores the result in PostgreSQL
6. Generates an alert and advisory checklist if the hive state is dangerous
7. Serves all results to the React Native mobile app via REST endpoints

---

## The 7-Step Inference Pipeline

```
Step 1 — Sensor records audio
   Audio sensor on farmer's external server writes .wav files to a folder:
   /home/farmer/recordings/hive1.wav, hive2.wav …

Step 2 — FastAPI polls the external server (every 30 s)
   Background job connects via HTTP API, lists available recordings,
   finds files not yet seen.

Step 3 — File path stored in DB as pending
   For each new file: INSERT INTO audio_sources (source_url, status='pending')
   No audio bytes are downloaded yet.

Step 4 — FastAPI fetches bytes + sends to HuggingFace
   Second background job (offset 10 s) picks up pending rows,
   downloads the audio bytes via HTTP API, and POSTs them to the
   HuggingFace Gradio Space (DerrickLegacy256/bee-audio-classifier).

Step 5 — Inference result comes back from HuggingFace
   The Gradio Space classifies the audio and returns:
   { "label": "swarming", "score": 0.983, "all_scores": {…} }

Step 6 — Result stored in DB
   INSERT INTO inference_results (hive_state, confidence_score, latency_ms)
   If state is "swarming" or "missing_queen":
     INSERT INTO alerts + advisories + advisory_actions

Step 7 — Mobile app reads results
   React Native app calls:
     GET /hives/{id}/inferences/latest   → current hive state
     GET /hives/{id}/alerts              → pending alerts
```

---

## Hive States

| State              | Meaning                   | Alert Generated           |
| ------------------ | ------------------------- | ------------------------- |
| `active_colony`    | Healthy, normal activity  | No                        |
| `queenbee_present` | Queen bee detected        | No                        |
| `swarming`         | Swarm event in progress   | **Yes — High priority**   |
| `missing_queen`    | Queen is absent           | **Yes — Medium priority** |
| `external_noise`   | Background / interference | No                        |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  FARMER'S EXTERNAL SERVER                                           │
│                                                                     │
│  Audio sensor → /home/farmer/recordings/hive1.wav                  │
│                                        hive2.wav  …                │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       │  HTTP API (with API key) — every 30 s
                       │  Step 1→2: poll for new files
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BSADS FastAPI SERVICE (localhost:8000)                             │
│                                                                     │
│  ① Discovery job — list recordings via API, register pending rows  │
│  ② Inference job — fetch bytes via API, POST to HuggingFace Space │
│  ③ Store result — InferenceResult + Alert + Advisory in Postgres   │
└──────┬──────────────────────────────────────────┬───────────────────┘
       │                                          │
       │  GET /hives/{id}/inferences/latest       │  POST /audio/upload
       │  GET /hives/{id}/alerts                  │  (manual upload option)
       ▼                                          ▼
┌──────────────────┐                    ┌─────────────────────────────┐
│  React Native    │                    │  Direct HTTP upload          │
│  Mobile App      │                    │  (testing / manual use)      │
└──────────────────┘                    └─────────────────────────────┘
                                                   │
                       ┌───────────────────────────┘
                       │  Audio bytes (HTTP POST)
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  HUGGINGFACE GRADIO SPACE                                           │
│  DerrickLegacy256/bee-audio-classifier                              │
│                                                                     │
│  Receives audio bytes → runs Gradient Boosting model               │
│  Returns: { label, score, all_scores }                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Where inference actually runs

The ML model runs inside the HuggingFace Gradio Space (`DerrickLegacy256/bee-audio-classifier`).
This API sends raw audio bytes to the Space and receives the classification result back — no model
files are downloaded or run locally.

The Space handles feature extraction (171 acoustic features: MFCCs, spectral features, etc.) and
runs the trained Gradient Boosting classifier internally.

The ML training pipeline (notebooks, feature extraction, model training) lives in the separate
`bee_swarming_audio_classifer/` project. When a new model is trained and pushed to HuggingFace,
the Space picks it up automatically.

---

## Farmer Data Sources — How Audio Reaches the API

### Option A — HTTP API polling (recommended, production use)

The farmer provides their server URL and API key during registration or via profile update.
The API connects every 30 seconds, lists new audio files via HTTP, downloads them, and sends
them for inference automatically.

**Benefits:**

- Simple setup (no SSH keys)
- Works through firewalls
- Easy to revoke access
- Farmer maintains control
- Auto-configured when user has credentials

**Setup guide:** See [USER_REGISTRATION_GUIDE.md](USER_REGISTRATION_GUIDE.md) and [FARMER_API_KEY_SETUP.md](FARMER_API_KEY_SETUP.md)

Configure via:

- User registration: `POST /auth/register` with `server_url` and `api_key`
- Profile update: `PUT /auth/me` with `server_url` and `api_key`
- Per-hive override: `POST /hives/{hive_id}/data-source/configure`

### Option B — Watched local folder (development / simple deployments)

Drop `.wav` files into `data_sources/{user_id}/{hive_id}/` on the server running the API.
The same poller picks them up every 30 seconds.

Created automatically when you register a hive.

### Option C — Direct HTTP upload (manual / testing)

Upload a recording directly via HTTP. Inference runs in the background and the result appears
in `/hives/{id}/inferences/latest` within a few seconds.

Upload via: `POST /audio/upload`

---

## Quick Start

See [SETUP.md](SETUP.md) for the full installation guide.

```bash
# 1. Clone and install
git clone <repo-url> && cd bsads_backend_and_fast_api
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env     # then edit with your DB credentials, HF tokens, etc.

# 3. Run
uvicorn api.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

---

## All API Endpoints

| Method | Endpoint                                    | Auth | Description                     |
| ------ | ------------------------------------------- | ---- | ------------------------------- |
| GET    | `/`                                         | No   | Health check                    |
| GET    | `/docs`                                     | No   | Swagger UI                      |
| GET    | `/redoc`                                    | No   | ReDoc reference                 |
| POST   | `/auth/register`                            | No   | Create farmer account           |
| POST   | `/auth/login`                               | No   | Login, get JWT token            |
| GET    | `/auth/me`                                  | Yes  | My profile                      |
| POST   | `/hives`                                    | Yes  | Register a hive                 |
| GET    | `/hives`                                    | Yes  | List my hives                   |
| GET    | `/hives/{id}`                               | Yes  | Get one hive                    |
| GET    | `/hives/{id}/data-source`                   | Yes  | Data source status              |
| POST   | `/hives/{id}/data-source/configure`         | Yes  | Configure HTTP API data source  |
| POST   | `/audio/upload`                             | Yes  | Upload audio file manually      |
| GET    | `/hives/{id}/inferences`                    | Yes  | All inference results (last 20) |
| GET    | `/hives/{id}/inferences/latest`             | Yes  | Most recent result              |
| GET    | `/hives/{id}/alerts`                        | Yes  | Pending alerts                  |
| PATCH  | `/hives/{id}/alerts/{alert_id}/acknowledge` | Yes  | Mark alert as acted on          |

---

## Project Structure

```
bsads_backend_and_fast_api/
├── api/
│   ├── main.py              ← FastAPI app, APScheduler startup
│   ├── config.py            ← Settings loaded from .env
│   ├── database.py          ← SQLAlchemy engine + session
│   ├── models.py            ← All ORM table definitions
│   ├── schemas.py           ← Pydantic request/response shapes
│   ├── inference_engine.py  ← Gradio client — sends audio to HF Space, returns result
│   ├── advisory.py          ← Alert + advisory generation rules
│   ├── processing.py        ← Shared inference pipeline (upload + poller both call this)
│   ├── poller.py            ← Two-phase background poller (discovery + inference jobs)
│   ├── http_connector.py    ← HTTP API connector for farmer's external servers
│   └── routers/
│       ├── auth.py          ← /auth/register, /auth/login, /auth/me
│       ├── hives.py         ← /hives and /hives/{id}/data-source/configure
│       ├── audio.py         ← /audio/upload
│       ├── inferences.py    ← /hives/{id}/inferences
│       └── alerts.py        ← /hives/{id}/alerts
├── hf_space/                ← HuggingFace Gradio Space source (deployed separately)
├── data_sources/            ← Watched folders per hive (created automatically)
├── uploads/                 ← Manual HTTP upload staging area
├── requirements.txt
├── Dockerfile
├── .env                     ← Not committed — create from .env.example
├── .env.example             ← Template — copy to .env and fill in values
├── SETUP.md                 ← Full installation guide
├── TESTING.md               ← 7-step pipeline test walkthrough with curl commands
└── API.md                   ← Deep technical documentation
```

---

## Documentation

| File                                               | Contents                                                                      |
| -------------------------------------------------- | ----------------------------------------------------------------------------- |
| [SETUP.md](SETUP.md)                               | Prerequisites, PostgreSQL setup, venv, .env config, first run                 |
| [TESTING.md](TESTING.md)                           | Full 7-step inference pipeline test with SSH simulation and all curl commands |
| [API.md](API.md)                                   | Deep technical docs: DB schema, advisory rules, endpoint reference            |
| [FARMER_API_KEY_SETUP.md](FARMER_API_KEY_SETUP.md) | How to connect to farmer's server using API keys (recommended method)         |
