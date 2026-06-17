# Complete Deployment Guide - BSADS API

## 🎯 Overview

This guide covers deploying the BSADS API with:
- ✅ FastAPI on port **8085**
- ✅ PostgreSQL exposed on port **5433** (for Laravel access)
- ✅ Docker networking fixed for same-host simulation server
- ✅ Persistent data volumes

---

## 📋 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Host Machine (196.43.168.57)                                │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Docker Container: bsads-api-production               │  │
│  │                                                       │  │
│  │  ┌─────────────┐        ┌─────────────────────────┐ │  │
│  │  │ PostgreSQL  │◄───────┤ FastAPI                 │ │  │
│  │  │ :5432       │        │ :8085                   │ │  │
│  │  └─────────────┘        │ - Poller                │ │  │
│  │                         │ - Inference Engine      │ │  │
│  │                         │ - API Routes            │ │  │
│  │                         └─────────────────────────┘ │  │
│  │                                  │                   │  │
│  │                                  │ via               │  │
│  │                                  │ host.docker       │  │
│  │                                  │ .internal         │  │
│  └──────────────────────────────────┼───────────────────┘  │
│           │              │           │                      │
│           │ :5433        │ :8085     │                      │
│           │              │           ▼                      │
│  ┌────────┴────────┐  ┌──┴─────────────────────────────┐  │
│  │ Laravel App     │  │ External Access                │  │
│  │ (Database       │  │ (API Users)                    │  │
│  │  Client)        │  │                                │  │
│  └─────────────────┘  └────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Farmer Simulation Server                             │  │
│  │ Port 8086                                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start - Choose Your Deployment Method

### Method 1: Automated Deployment (GitHub Actions) ⭐ RECOMMENDED

```bash
# 1. Ensure GitHub Secrets are configured (see below)
# 2. Commit your changes
git add .
git commit -m "Deploy BSADS API with all fixes"

# 3. Push to main branch to trigger deployment
git push origin main

# 4. Monitor deployment at:
# https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

**What it does:**
- Builds Docker image with latest code
- Pushes to Docker Hub
- SSHs to production server
- Deploys with correct configuration
- Exposes ports 8085 (API) and 5433 (PostgreSQL)

---

### Method 2: Manual Deployment (Quick Fix)

```bash
# SSH to your server
ssh ademneadev@196.43.168.57

# Option A: Expose PostgreSQL for Laravel
bash expose_postgres.sh

# Option B: Use host network mode (if simulation server issues)
bash deploy_with_host_network.sh

# Option C: Full diagnostic first
bash diagnose_connection.sh
```

---

## 🔑 GitHub Secrets Required

Go to: **GitHub Repo → Settings → Secrets and variables → Actions**

Add these secrets:

| Secret Name | Description | Example |
|------------|-------------|---------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username | `bsads2026` |
| `DOCKERHUB_TOKEN` | Docker Hub access token | Get from hub.docker.com |
| `SERVER_PASSWORD` | SSH password for server | Your server password |
| `SECRET_KEY` | JWT secret for production | Generate with `openssl rand -hex 32` |
| `HF_SPACE_NAME` | HuggingFace space name | `DerrickLegacy256/bee-audio-classifier` |
| `HF_TOKEN` | HuggingFace API token | Get from huggingface.co |

---

## 📡 Exposed Services

### FastAPI (Port 8085)
- **URL:** http://196.43.168.57:8085
- **Docs:** http://196.43.168.57:8085/docs
- **Health:** http://196.43.168.57:8085/health
- **Purpose:** Main API for mobile apps and web clients

### PostgreSQL (Port 5433)
- **Host:** 196.43.168.57
- **Port:** 5433 (external) → 5432 (internal)
- **Database:** bee_db
- **Username:** bee_user
- **Password:** bee_user
- **Purpose:** Database access for Laravel app

---

## 🔧 Laravel Configuration

### Step 1: Update Laravel .env

```env
DB_CONNECTION=pgsql
DB_HOST=196.43.168.57
DB_PORT=5433
DB_DATABASE=bee_db
DB_USERNAME=bee_user
DB_PASSWORD=bee_user
```

### Step 2: Test Connection

```bash
# Clear config cache
php artisan config:clear

# Test connection
php artisan tinker
>>> DB::connection()->getPdo();
>>> DB::select('SELECT version()');

# List tables
php artisan db:show
```

### Step 3: Use Database in Laravel

```php
// Example: Get users
$users = DB::table('users')->get();

// Example: Get hives
$hives = DB::table('hives')->where('owner_id', $userId)->get();

// Example: Get latest inferences
$inferences = DB::table('audio_sources')
    ->join('inferences', 'audio_sources.id', '=', 'inferences.audio_source_id')
    ->where('audio_sources.hive_id', $hiveId)
    ->orderBy('inferences.created_at', 'desc')
    ->get();
```

---

## 🐛 Troubleshooting

### Issue 1: API Not Accessible (http://196.43.168.57:8085)

**Symptoms:**
- Cannot reach API
- Connection refused or timeout

**Solutions:**
```bash
# Check if container is running
docker ps | grep bsads-api-production

# Check if port is mapped
docker ps | grep 8085
# Should show: 0.0.0.0:8085->8085/tcp

# Check logs
docker logs -f bsads-api-production

# Restart container
bash expose_postgres.sh
```

---

### Issue 2: Container Cannot Reach Simulation Server (Port 8086)

**Symptoms:**
- Logs show: `Connection to host.docker.internal timed out`
- Folder creation fails

**Solutions:**

**Step 1: Verify simulation server is running**
```bash
curl http://localhost:8086/health
```

If this fails, **start your simulation server first!**

**Step 2: Check host.docker.internal is configured**
```bash
docker exec bsads-api-production cat /etc/hosts | grep host.docker.internal
# Should show an IP
```

**Step 3: Run full diagnostics**
```bash
bash diagnose_connection.sh
```

**Quick Fix: Use host network mode**
```bash
bash deploy_with_host_network.sh
```

This allows the container to access `localhost:8086` directly.

---

### Issue 3: Laravel Cannot Connect to Database

**Symptoms:**
- `SQLSTATE[08006] [7] could not connect to server`
- Connection refused on port 5433

**Solutions:**

**Step 1: Check if port is exposed**
```bash
docker ps | grep bsads-api-production
# Should show: 0.0.0.0:5433->5432/tcp
```

**Step 2: Test from server itself**
```bash
psql -h 196.43.168.57 -p 5433 -U bee_user -d bee_db
# Password: bee_user
```

**Step 3: Check firewall (if Laravel on different server)**
```bash
# On API server, allow port 5433
sudo ufw allow 5433/tcp

# Or allow from specific Laravel server IP
sudo ufw allow from LARAVEL_IP to any port 5433
```

**Step 4: Redeploy with PostgreSQL exposed**
```bash
bash expose_postgres.sh
```

---

### Issue 4: "No active data sources to scan"

**Cause:** No hives have been created or linked to farmers

**Solution:**

1. **Create a user (farmer):**
```bash
curl -X POST http://196.43.168.57:8085/bsads-api-db/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "full_name": "Test Farmer",
    "email": "farmer@example.com",
    "password": "password123",
    "phone": "0700000000",
    "address": "Test Address",
    "role": "farmer",
    "server_url": "http://196.43.168.57:8086/",
    "api_key": "your-simulation-api-key"
  }'
```

2. **Login to get token:**
```bash
curl -X POST http://196.43.168.57:8085/bsads-api-db/auth/login \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "farmer@example.com",
    "password": "password123"
  }'
```

3. **Create a hive:**
```bash
curl -X POST http://196.43.168.57:8085/bsads-api-db/hives \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "hive_name": "Test Hive 01",
    "hive_location": "Test Location",
    "hive_type": "Box",
    "installation_date": "2026-06-17",
    "latitude": 0.39,
    "longitude": 0.98,
    "owner_id": "USER_ID_FROM_LOGIN"
  }'
```

---

## 📊 Monitoring & Logs

### View Container Logs
```bash
# Real-time logs
docker logs -f bsads-api-production

# Last 100 lines
docker logs --tail 100 bsads-api-production

# Filter for errors
docker logs bsads-api-production 2>&1 | grep -i error

# Filter for URL translation
docker logs bsads-api-production 2>&1 | grep Translating
```

### View Specific Service Logs
```bash
# FastAPI logs
docker exec -it bsads-api-production tail -f /var/log/supervisor/fastapi.log

# PostgreSQL logs
docker exec -it bsads-api-production tail -f /var/log/supervisor/postgresql.log

# Supervisor logs
docker exec -it bsads-api-production tail -f /var/log/supervisor/supervisord.log
```

### Check Service Status
```bash
# Inside container
docker exec -it bsads-api-production supervisorctl status

# Expected output:
# fastapi     RUNNING   pid 123, uptime 0:10:00
# postgresql  RUNNING   pid 124, uptime 0:10:00
```

---

## 🔐 Security Recommendations

### 1. Change Default Database Password

```bash
docker exec -it bsads-api-production bash
su - postgres
psql

ALTER USER bee_user WITH PASSWORD 'strong_new_password';
\q
exit
exit

# Update environment variables
docker stop bsads-api-production
docker rm bsads-api-production

# Redeploy with new password
docker run -d ... \
  -e DATABASE_URL="postgresql://bee_user:strong_new_password@localhost:5432/bee_db" \
  ...
```

### 2. Create Separate Laravel Database User

```bash
docker exec -it bsads-api-production bash
su - postgres
psql -d bee_db

-- Read-only user for Laravel
CREATE USER laravel_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE bee_db TO laravel_readonly;
GRANT USAGE ON SCHEMA public TO laravel_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO laravel_readonly;

-- Grant SELECT on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO laravel_readonly;

\q
exit
exit
```

Laravel `.env`:
```env
DB_USERNAME=laravel_readonly
DB_PASSWORD=secure_password
```

### 3. Configure Firewall

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow API
sudo ufw allow 8085/tcp

# Allow PostgreSQL from specific IP only
sudo ufw allow from LARAVEL_SERVER_IP to any port 5433

# Enable firewall
sudo ufw enable
```

---

## 📦 Data Persistence

### Docker Volumes

Your data is stored in Docker volumes and persists across container restarts:

```bash
# List volumes
docker volume ls | grep bsads

# Inspect volume
docker volume inspect bsads-data
docker volume inspect bsads-uploads

# Backup database
docker exec bsads-api-production pg_dump -U bee_user bee_db > backup_$(date +%Y%m%d).sql

# Restore database
cat backup_20260617.sql | docker exec -i bsads-api-production psql -U bee_user bee_db
```

---

## 🔄 Updates & Redeployment

### Update via GitHub Actions
```bash
# Simply push to main
git add .
git commit -m "Update feature X"
git push origin main
```

### Manual Update
```bash
ssh ademneadev@196.43.168.57

# Pull latest image
docker pull bsads2026/bsads-api:latest

# Restart container
docker stop bsads-api-production
docker rm bsads-api-production
bash expose_postgres.sh
```

---

## ✅ Final Checklist

- [ ] GitHub Secrets configured
- [ ] Code pushed to main branch
- [ ] Deployment successful (check GitHub Actions)
- [ ] API accessible: `curl http://196.43.168.57:8085/health`
- [ ] PostgreSQL accessible from Laravel
- [ ] Simulation server running on port 8086
- [ ] Container can reach simulation server (no timeouts in logs)
- [ ] Farmer account created
- [ ] Test hive created successfully
- [ ] Folder creation working (`folder_created: true`)
- [ ] Laravel can query database

---

## 📚 Additional Documentation

- **`LARAVEL_DATABASE_ACCESS.md`** - Detailed Laravel integration guide
- **`TROUBLESHOOTING.md`** - Common issues and solutions
- **`DOCKER_NETWORKING_FIX.md`** - Technical details on networking
- **`PRE_PUSH_CHECKLIST.md`** - Pre-deployment checklist

---

## 🆘 Support

If you encounter issues:

1. **Run diagnostics:** `bash diagnose_connection.sh`
2. **Check logs:** `docker logs -f bsads-api-production`
3. **Verify services:** `docker ps` and `supervisorctl status`
4. **Test connectivity:** `curl` commands in troubleshooting section

---

## 🎉 Summary

Your BSADS API is now deployed with:
- ✅ FastAPI accessible on port 8085
- ✅ PostgreSQL accessible on port 5433 for Laravel
- ✅ Docker networking configured for same-host communication
- ✅ Persistent data storage
- ✅ Automated deployment via GitHub Actions

**You're all set!** 🚀
