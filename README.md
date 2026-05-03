# BSADS — FastAPI Backend Service

**Bee Swarming & Abscondment Detection System**

This is the production API for the BSADS project. It connects farmers' remote audio sensors to a trained ML model, stores inference results, generates alerts, and serves data to the mobile app.

---

## What This Service Does

Beehive audio sensors record sound continuously. This API:

1. Connects to the farmer's external server via SSH and polls for new recordings
2. Extracts 171 acoustic features from each recording (MFCCs, spectral features, etc.)
3. Runs the recording through the trained Gradient Boosting model
4. Stores the result and raises an alert if a dangerous hive state is detected
5. Serves results to the React Native mobile app

---

## Hive States

| State | Meaning | Alert Generated |
|---|---|---|
| `active_colony` | Healthy, normal activity | No |
| `queenbee_present` | Queen bee detected | No |
| `swarming` | Swarm event in progress | **Yes — High priority** |
| `missing_queen` | Queen is absent | **Yes — Medium priority** |
| `external_noise` | Background / interference | No |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FARMER'S EXTERNAL SERVER                         │
│                                                                     │
│   Audio sensor → /home/farmer/recordings/hive1.wav                 │
│                                    hive2.wav                        │
│                                    hive3.wav  ...                   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            │  SSH/SFTP (paramiko)
                            │  every 30 seconds
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BSADS FastAPI SERVICE                            │
│                                                                     │
│  ① Poller detects new .wav files on remote server                  │
│  ② Downloads file → staging: downloads/{user_id}/{hive_id}/        │
│  ③ Creates audio_source record (status=pending)                    │
│  ④ Extracts 171 features using librosa                             │
│  ⑤ Loads model from HuggingFace Hub (cached after first run)       │
│  ⑥ Runs inference → hive_state + confidence_score                  │
│  ⑦ If swarming or missing_queen → creates Alert + Advisory         │
│  ⑧ Stores everything in PostgreSQL                                 │
└───────┬──────────────────────────────────────────────────┬──────────┘
        │                                                  │
        │  GET /hives/{id}/inferences/latest               │  POST /audio/upload
        │  GET /hives/{id}/alerts                          │  (manual upload option)
        ▼                                                  ▼
┌───────────────────┐                           ┌──────────────────────┐
│  React Native     │                           │  Farmer uploads      │
│  Mobile App       │                           │  directly via API    │
└───────────────────┘                           └──────────────────────┘
```

### Where the ML model lives

The model (`gradient_boosting_model.pkl`) and encoder (`label_encoder.pkl`) are hosted on HuggingFace Hub at `DerrickLegacy256/bee-audio-classifier`. At startup the API downloads them once and caches them locally — restarts are instant after that.

The ML training pipeline (notebooks, feature extraction, model training) lives in the separate `bee_swarming_audio_classifer/` project. When a new model is trained and pushed to HuggingFace via CI/CD, simply restarting this API picks it up automatically.

---

## Farmer Data Sources — Two Ways Audio Reaches the API

### Option A — SSH polling (primary)
The farmer provides SSH credentials to their remote server. The API connects every 30 seconds, lists new audio files, downloads them, and runs inference automatically.

Configure via: `POST /hives/{hive_id}/data-source/configure`

### Option B — Direct upload (manual)
The farmer uploads a recording directly via HTTP.

Upload via: `POST /audio/upload`

---

## Quick Start

See [SETUP.md](SETUP.md) for the full installation guide.

```bash
# 1. Clone and install
git clone <repo-url> && cd bsads_fast_api
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env     # then edit with your DB credentials

# 3. Run
uvicorn api.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

---

## All API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Health check |
| GET | `/docs` | No | Swagger UI |
| GET | `/redoc` | No | ReDoc reference |
| POST | `/auth/register` | No | Create farmer account |
| POST | `/auth/login` | No | Login, get JWT token |
| GET | `/auth/me` | Yes | My profile |
| POST | `/hives` | Yes | Register a hive |
| GET | `/hives` | Yes | List my hives |
| GET | `/hives/{id}` | Yes | Get one hive |
| GET | `/hives/{id}/data-source` | Yes | Data source status |
| POST | `/hives/{id}/data-source/configure` | Yes | Configure SSH data source |
| POST | `/audio/upload` | Yes | Upload audio file manually |
| GET | `/hives/{id}/inferences` | Yes | All inference results (last 20) |
| GET | `/hives/{id}/inferences/latest` | Yes | Most recent result |
| GET | `/hives/{id}/alerts` | Yes | Pending alerts |
| PATCH | `/hives/{id}/alerts/{alert_id}/acknowledge` | Yes | Mark alert as acted on |

---

## Project Structure

```
bsads_fast_api/
├── api/
│   ├── main.py              ← FastAPI app, APScheduler startup
│   ├── config.py            ← Settings loaded from .env
│   ├── database.py          ← SQLAlchemy engine + session
│   ├── models.py            ← All 11 ORM table definitions
│   ├── schemas.py           ← Pydantic request/response shapes
│   ├── inference_engine.py  ← Feature extraction + model prediction
│   ├── advisory.py          ← Alert + advisory generation rules
│   ├── processing.py        ← Shared inference pipeline (used by upload + poller)
│   ├── poller.py            ← Background folder + SSH scanner (every 30s)
│   ├── ssh_connector.py     ← Paramiko SSH/SFTP connector
│   └── routers/
│       ├── auth.py          ← /auth/register, /auth/login, /auth/me
│       ├── hives.py         ← /hives and /hives/{id}/data-source/configure
│       ├── audio.py         ← /audio/upload
│       ├── inferences.py    ← /hives/{id}/inferences
│       └── alerts.py        ← /hives/{id}/alerts
├── requirements.txt
├── Dockerfile
├── .env                     ← Not committed — create from .env.example
├── SETUP.md                 ← Full installation guide
├── TESTING.md               ← End-to-end test walkthrough
└── API.md                   ← Deep technical documentation
```

---

## Documentation

| File | Contents |
|---|---|
| [SETUP.md](SETUP.md) | Prerequisites, PostgreSQL setup, venv, .env config, first run |
| [TESTING.md](TESTING.md) | Full end-to-end test with SSH simulation, all curl commands |
| [API.md](API.md) | Deep technical docs: DB schema, inference pipeline, advisory rules |
