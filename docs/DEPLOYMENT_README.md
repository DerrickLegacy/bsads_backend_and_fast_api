# 🚀 Automated Server Deployment

Deploy your BSADS API to `196.43.168.57:8080` automatically via GitHub Actions.

---

## 🤖 How It Works

**Push to `main` → GitHub Actions → Docker Hub → Your Server**

Every push automatically:
1. Builds Docker image (PostgreSQL + FastAPI in one container)
2. Pushes to Docker Hub
3. Deploys to your server
4. Restarts the container
5. Verifies it's working

---

## ⚙️ One-Time Setup

### 1. Create GitHub Secrets

Go to: **Repository → Settings → Secrets and variables → Actions**

Click **New repository secret** for each:

```bash
DOCKERHUB_USERNAME     # Your Docker Hub username
DOCKERHUB_TOKEN        # Docker Hub access token (Settings → Security)
SERVER_PASSWORD        # Ademneadev@26
DATABASE_URL           # postgresql://bee_user:bee_user@localhost:5432/bee_db
SECRET_KEY             # Generate: python3 -c "import secrets; print(secrets.token_hex(32))"
HF_SPACE_NAME          # DerrickLegacy256/bee-audio-classifier
HF_TOKEN               # Your HuggingFace token
```

### 2. Prepare Server (One-Time)

SSH to server and create volumes:

```bash
ssh ademneadev@196.43.168.57

# Create persistent storage
docker volume create bsads-data
docker volume create bsads-uploads

# Open firewall
sudo ufw allow 8080/tcp

exit
```

---

## 🚀 Deploy

### Automatic (Recommended)
```bash
git add .
git commit -m "Your changes"
git push origin main
```

GitHub Actions deploys automatically!

### Manual Trigger
1. Go to **Actions** tab
2. Click **Deploy to Production Server**
3. Click **Run workflow**

---

## 🏗️ Architecture

### Single Docker Container
```
┌─────────────────────────────────┐
│  Supervisor (process manager)   │
│  ├─ PostgreSQL (port 5432)     │
│  └─ FastAPI (port 8080)        │
└─────────────────────────────────┘
         ↓
   Docker Volumes
   ├─ bsads-data (database)
   └─ bsads-uploads (files)
```

**Why Supervisor?**
- Manages both PostgreSQL and FastAPI processes
- Auto-restarts if either crashes
- Ensures correct startup order
- Provides unified logging

---

## 🌐 API Endpoints

**Base URL**: `http://196.43.168.57:8080`

- Health: http://196.43.168.57:8080/health
- Docs: http://196.43.168.57:8080/docs
- ReDoc: http://196.43.168.57:8080/redoc

Replace Railway URL in your apps:
```
Old: https://bsads-api-production.up.railway.app
New: http://196.43.168.57:8080
```

---

## 📊 Monitor Deployments

### GitHub Actions
- Go to **Actions** tab
- View deployment status
- See logs and summaries

### Server Logs
```bash
# Real-time logs
ssh ademneadev@196.43.168.57 'docker logs -f bsads-api-production'

# Last 100 lines
ssh ademneadev@196.43.168.57 'docker logs --tail 100 bsads-api-production'
```

### Health Check
```bash
curl http://196.43.168.57:8080/health
```

---

## 🛠️ Common Tasks

### Restart Container
```bash
ssh ademneadev@196.43.168.57 'docker restart bsads-api-production'
```

### Check Status
```bash
ssh ademneadev@196.43.168.57 'docker ps | grep bsads'
```

### Supervisor Status
```bash
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production supervisorctl status'
```

### Database Backup
```bash
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production pg_dump -U bee_user bee_db' > backup.sql
```

### Database Restore
```bash
cat backup.sql | ssh ademneadev@196.43.168.57 'docker exec -i bsads-api-production psql -U bee_user bee_db'
```

---

## 🐛 Troubleshooting

### Check Deployment Logs
1. GitHub → Actions tab
2. Click latest workflow run
3. View step-by-step logs

### Container Not Running?
```bash
ssh ademneadev@196.43.168.57 'docker ps -a | grep bsads'
ssh ademneadev@196.43.168.57 'docker logs bsads-api-production'
```

### API Not Responding?
```bash
# Test from server
ssh ademneadev@196.43.168.57 'curl localhost:8080/health'

# Check processes
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production ps aux'
```

---

## 📁 Key Files

- `.github/workflows/deploy.yml` - GitHub Actions workflow
- `Dockerfile.production` - Production Docker image
- `supervisord.conf` - Process manager config
- `start_production.sh` - Startup script with migrations
- `test_deployment.sh` - Verification script

---

## 💡 Pro Tips

**Data Persistence**: Docker volumes preserve data across deployments

**Zero Downtime**: Old container stops only after new one is ready

**Rollback**: Redeploy previous commit to roll back

**Environment**: All secrets managed via GitHub Secrets

---

## 🎯 Summary

1. **Setup once**: GitHub Secrets + Docker volumes
2. **Deploy**: Push to `main` branch
3. **Monitor**: GitHub Actions tab
4. **Manage**: SSH when needed

**Fully automated, no manual steps!** 🎉

See `AUTOMATED_DEPLOYMENT.md` for detailed documentation.
