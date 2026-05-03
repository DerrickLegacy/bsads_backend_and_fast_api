# BSADS FastAPI — Setup Guide

Everything you need to get the server running from scratch.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | Use `python3 --version` to check |
| PostgreSQL | 14+ | Must be running before the API starts |
| libsndfile | any | Required by librosa for audio processing |
| ffmpeg | any | Required by librosa for non-WAV formats |

Install system dependencies on Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y libsndfile1 ffmpeg postgresql postgresql-contrib
```

---

## Step 1 — Create the PostgreSQL database

The API connects to a PostgreSQL database called `bee_db` using the credentials `bee_user / bee_user`.

Open a `psql` shell and run:

```sql
-- Create the database user
CREATE USER bee_user WITH PASSWORD 'bee_user';

-- Create the database owned by that user
CREATE DATABASE bee_db OWNER bee_user;

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE bee_db TO bee_user;
```

To verify it worked:
```bash
psql -U bee_user -d bee_db -c "\dt"
# Should connect without errors (tables will be empty — they are created by the API on first run)
```

If PostgreSQL is not running:
```bash
sudo service postgresql start
# or
sudo systemctl start postgresql
```

---

## Step 2 — Create a Python virtual environment

```bash
cd /path/to/bsads_fast_api

python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

This installs all dependencies: FastAPI, SQLAlchemy, librosa, scikit-learn, paramiko, apscheduler, and others.

---

## Step 3 — Configure the environment file

Create `.env` in the project root (copy the example below):

```bash
cp .env.example .env
```

Then edit `.env`:

```env
# HuggingFace — used to download the model at startup
# Get your token at https://huggingface.co/settings/tokens
HF_TOKEN=hf_your_token_here

# PostgreSQL connection string
DATABASE_URL=postgresql://bee_user:bee_user@localhost:5432/bee_db

# JWT secret — change this in production to a long random string
SECRET_KEY=change-this-to-a-long-random-secret-in-production

# Folder where manually uploaded audio files are saved
UPLOAD_DIR=uploads
```

**Do not commit `.env` to git.** It is already in `.gitignore`.

### Create `.env.example` for teammates

```bash
cat > .env.example << 'EOF'
HF_TOKEN=
DATABASE_URL=postgresql://bee_user:bee_user@localhost:5432/bee_db
SECRET_KEY=change-this-in-production
UPLOAD_DIR=uploads
EOF
```

---

## Step 4 — Start the server

```bash
# Make sure venv is activated
source venv/bin/activate

uvicorn api.main:app --reload --port 8000
```

On first run you should see:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
✓ gradient_boosting_model.pkl loaded from HuggingFace Hub (cached)
✓ label_encoder.pkl loaded from HuggingFace Hub (cached)
✓ Database tables ready
✓ Upload directory ready
✓ data_sources/ folder ready (drop audio files here per hive)
✓ Model repo: DerrickLegacy256/bee-audio-classifier
✓ Folder + SSH poller started — scanning every 30 seconds
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

The model is downloaded from HuggingFace on the first startup and cached at `~/.cache/huggingface/hub/`. Subsequent starts load from cache — no internet required after the first run.

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
  -e HF_TOKEN=your-hf-token \
  bsads-api
```

Note: `host.docker.internal` points to your host machine's PostgreSQL from inside the container. On Linux you may need to use `--network host` instead.

---

## Troubleshooting

### "could not connect to server" on startup
PostgreSQL is not running. Start it:
```bash
sudo service postgresql start
```

### "FATAL: role bee_user does not exist"
The database user was not created. Re-run Step 1.

### "No module named 'librosa'" or similar
The venv is not activated, or `pip install -r requirements.txt` did not complete.
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Model fails to download from HuggingFace
Check your `HF_TOKEN` in `.env`. For public repos the token is optional, but set it anyway.
The API also falls back to local model files — place `gradient_boosting_model.pkl` and
`label_encoder.pkl` in a `models/` folder in the project root if needed.

### Port 8000 already in use
```bash
# Find what is using it
lsof -i :8000
# Kill it, or run on a different port
uvicorn api.main:app --reload --port 8001
```
