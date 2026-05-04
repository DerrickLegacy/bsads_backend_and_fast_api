# BSADS FastAPI — Setup Guide

Everything you need to get the server running from scratch.

---

## Prerequisites

| Requirement | Version | Notes                                    |
| ----------- | ------- | ---------------------------------------- |
| Python      | 3.10+   | Use `python3 --version` to check         |
| PostgreSQL  | 14+     | Must be running before the API starts    |

Install on Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

> **Note:** `librosa`, `ffmpeg`, and `libsndfile` are **not required** — audio feature extraction
> runs inside the HuggingFace Gradio Space, not locally. The API only sends raw audio bytes over HTTP.

---

## Step 1 — Create the PostgreSQL database

The API connects to a database called `bee_db` with credentials `bee_user / bee_user`.

Open a `psql` shell and run:

```sql
CREATE USER bee_user WITH PASSWORD 'bee_user';
CREATE DATABASE bee_db OWNER bee_user;
GRANT ALL PRIVILEGES ON DATABASE bee_db TO bee_user;
```

Verify it worked:

```bash
psql -U bee_user -d bee_db -c "\dt"
# Should connect without errors (tables are created by the API on first run)
```

If PostgreSQL is not running:

```bash
sudo systemctl start postgresql
```

---

## Step 2 — Create a Python virtual environment

```bash
cd /path/to/bsads_backend_and_fast_api

python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 3 — Configure the environment file

```bash
cp .env.example .env
```

Edit `.env` — the required values are marked below:

```env
# ── Required ──────────────────────────────────────────────────────────────────

DATABASE_URL=postgresql://bee_user:bee_user@localhost:5432/bee_db

# Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-long-random-secret-here

# The HuggingFace Gradio Space that runs inference
HF_SPACE_NAME=DerrickLegacy256/bee-audio-classifier

# ── Optional ──────────────────────────────────────────────────────────────────

# HF read token — required only if your Space is private
HF_TOKEN=

# HF write token — only needed for CI/CD model pushes, not for running the API
HF_WRITE_TOKEN=

# HF model repository (informational — CI/CD use only)
HF_MODEL_ID=DerrickLegacy256/bee_swarming_and_absconment

# Folder where manually uploaded audio files are saved
UPLOAD_DIR=uploads

# Poller timing (seconds) — increase if HF Space is slow to respond
POLL_INTERVAL_SECONDS=30
POLL_OFFSET_SECONDS=10
INFERENCE_TIMEOUT_SECONDS=240
```

**Do not commit `.env` to git.** It is already in `.gitignore`.

---

## Step 4 — Start the server

```bash
source venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

On first run you should see:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
✓ Database tables ready
✓ Upload directory ready
✓ data_sources/ folder ready (drop audio files here per hive)
✓ HuggingFace Space: DerrickLegacy256/bee-audio-classifier
✓ Discovery poller started — scanning every 30 seconds
✓ Inference poller started — processing pending records every 30 seconds
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

> The HuggingFace Gradio client connects lazily — it will only establish a connection on the
> first inference call, not at startup. This prevents a crash if the Space is waking up.

---

## Step 5 — Verify it is working

```bash
curl -s http://localhost:8000/ | python3 -m json.tool
```

Expected response:

```json
{
  "status": "ok",
  "service": "BSADS API v1.1.0",
  "docs": "http://localhost:8000/docs",
  "redoc": "http://localhost:8000/redoc"
}
```

Open interactive API docs in your browser:

- **http://localhost:8000/docs** — Swagger UI (try all endpoints here)
- **http://localhost:8000/redoc** — ReDoc (cleaner reading)

---

## Running with Docker

```bash
docker build -t bsads-api .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://bee_user:bee_user@host.docker.internal:5432/bee_db \
  -e SECRET_KEY=your-secret \
  -e HF_SPACE_NAME=DerrickLegacy256/bee-audio-classifier \
  -e HF_TOKEN=your-hf-token \
  bsads-api
```

On Linux use `--network host` instead of `host.docker.internal` for the DB connection.

---

## Troubleshooting

### "could not connect to server" on startup

PostgreSQL is not running:

```bash
sudo systemctl start postgresql
```

### "FATAL: role bee_user does not exist"

The database user was not created. Re-run Step 1.

### "No module named …" or import errors

The venv is not activated, or `pip install -r requirements.txt` did not complete:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "ValidationError: 1 validation error for Settings — secret_key — Field required"

`SECRET_KEY` is not set in your `.env`. Add it and restart.

### "ValidationError … hf_space_name — Field required"

`HF_SPACE_NAME` is not set in your `.env`. Add it and restart.

### Inference times out or returns no result

- The HuggingFace Space may be sleeping (free tier spins down after inactivity).
  Visit the Space URL in a browser to wake it up, then re-upload or wait for the next poll cycle.
- Increase `INFERENCE_TIMEOUT_SECONDS` in `.env` if you have a slow connection.

### Port 8000 already in use

```bash
lsof -i :8000          # find what is using it
uvicorn api.main:app --reload --port 8001   # or run on a different port
```
