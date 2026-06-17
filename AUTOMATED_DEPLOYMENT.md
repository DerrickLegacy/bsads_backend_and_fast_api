# 🤖 Automated Deployment Guide

This project uses **GitHub Actions** for fully automated deployment to your production server.

---

## 🏗️ Architecture

### What is Supervisor?
**Supervisor** is a process control system that manages both PostgreSQL and FastAPI inside the single Docker container:

```
Docker Container (bsads-api-production)
├── Supervisor (process manager)
│   ├── PostgreSQL (database on port 5432)
│   └── FastAPI/Uvicorn (API on port 8080)
└── Data Volumes
    ├── bsads-data (database files)
    └── bsads-uploads (audio files)
```

**Why Supervisor?**
- Keeps both processes running
- Auto-restarts if either crashes
- Manages startup order (DB starts before API)
- Provides unified logging

---

## 🚀 Setup (One-Time)

### 1. Create GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

| Secret Name | Value | Where to Get |
|------------|-------|--------------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username | [hub.docker.com](https://hub.docker.com) |
| `DOCKERHUB_TOKEN` | Docker Hub access token | [Docker Hub → Account Settings → Security → New Access Token](https://hub.docker.com/settings/security) |
| `SERVER_PASSWORD` | `Ademneadev@26` | Provided |
| `DATABASE_URL` | `postgresql://bee_user:bee_user@localhost:5432/bee_db` | Default (already in container) |
| `SECRET_KEY` | Generate: `python3 -c "import secrets; print(secrets.token_hex(32))"` | Run command locally |
| `HF_SPACE_NAME` | `DerrickLegacy256/bee-audio-classifier` | Your HuggingFace Space |
| `HF_TOKEN` | Your HuggingFace token | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

### 2. One-Time Server Setup (SSH)

Connect to your server and create Docker volumes:

```bash
ssh ademneadev@196.43.168.57

# Create persistent volumes
docker volume create bsads-data
docker volume create bsads-uploads

# Open firewall (if needed)
sudo ufw allow 8080/tcp

# Exit
exit
```

That's it! Server is ready.

---

## 📦 How Deployment Works

### Automatic Deployment

Every time you push to `main` branch:

1. ✅ GitHub Actions builds Docker image
2. ✅ Pushes image to Docker Hub
3. ✅ SSHs into your server
4. ✅ Pulls latest image
5. ✅ Stops old container
6. ✅ Starts new container with your code
7. ✅ Tests health endpoint
8. ✅ Reports success/failure

### Manual Deployment

You can also trigger deployment manually:

1. Go to: **Actions** tab in GitHub
2. Click: **Deploy to Production Server**
3. Click: **Run workflow** → **Run workflow**

---

## 🌐 Your Deployed API

**Base URL**: `http://196.43.168.57:8080`

**Endpoints**:
- Health: http://196.43.168.57:8080/health
- API Docs: http://196.43.168.57:8080/docs
- ReDoc: http://196.43.168.57:8080/redoc

---

## 🔍 Monitoring

### Check Deployment Status

1. Go to **Actions** tab in GitHub
2. View latest workflow run
3. See deployment summary at the bottom

### View Container Logs

```bash
ssh ademneadev@196.43.168.57 'docker logs -f bsads-api-production'
```

### Check Container Status

```bash
ssh ademneadev@196.43.168.57 'docker ps | grep bsads'
```

### Test Health

```bash
curl http://196.43.168.57:8080/health
```

---

## 🔄 Updating Your API

Just push to `main` branch:

```bash
git add .
git commit -m "Updated feature"
git push origin main
```

GitHub Actions automatically deploys! ✨

---

## 💾 Data Persistence

Your data is safe across deployments:

- **Database**: Stored in `bsads-data` Docker volume
- **Uploads**: Stored in `bsads-uploads` Docker volume

These volumes persist even when container is recreated.

---

## 🛠️ Management Commands

### Restart Container
```bash
ssh ademneadev@196.43.168.57 'docker restart bsads-api-production'
```

### View Logs
```bash
# All logs
ssh ademneadev@196.43.168.57 'docker logs bsads-api-production'

# Follow logs (real-time)
ssh ademneadev@196.43.168.57 'docker logs -f bsads-api-production'

# Last 100 lines
ssh ademneadev@196.43.168.57 'docker logs --tail 100 bsads-api-production'
```

### Access Container Shell
```bash
ssh ademneadev@196.43.168.57 'docker exec -it bsads-api-production bash'
```

### Check Supervisor Status (inside container)
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

### Deployment Failed?

1. Check GitHub Actions logs
2. View container logs: `docker logs bsads-api-production`
3. Check container is running: `docker ps | grep bsads`

### Container Won't Start?

```bash
# View logs
ssh ademneadev@196.43.168.57 'docker logs bsads-api-production'

# Check if port is already in use
ssh ademneadev@196.43.168.57 'sudo netstat -tulpn | grep 8080'
```

### API Not Responding?

```bash
# Test from server
ssh ademneadev@196.43.168.57 'curl localhost:8080/health'

# Test from container
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production curl localhost:8080/health'

# Check processes
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production ps aux'
```

### Database Issues?

```bash
# Check PostgreSQL is running
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production ps aux | grep postgres'

# Test connection
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production psql -U bee_user -d bee_db -c "SELECT 1"'

# Check supervisor status
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production supervisorctl status'
```

---

## 🔐 Security Notes

✅ **Secrets are secure**: GitHub Secrets are encrypted and never exposed in logs  
✅ **Docker token authentication**: Using Docker Hub token (not password)  
✅ **Data persistence**: Volumes ensure data survives deployments  
✅ **Auto-restart**: Container restarts on failure  

⚠️ **Recommendations**:
- Change PostgreSQL password in `Dockerfile.production` before first deploy
- Use nginx reverse proxy with SSL for production
- Setup subdomain instead of IP:port
- Schedule regular database backups

---

## 🌐 Optional: Subdomain Setup

Instead of `http://196.43.168.57:8080`, use `https://api.yourdomain.com`

### 1. Point DNS
Create A record: `api.yourdomain.com → 196.43.168.57`

### 2. Install Nginx (on server)
```bash
ssh ademneadev@196.43.168.57
sudo apt update && sudo apt install nginx
```

### 3. Configure Nginx
Create `/etc/nginx/sites-available/bsads-api`:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Enable
```bash
sudo ln -s /etc/nginx/sites-available/bsads-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Add SSL
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

Now accessible at: `https://api.yourdomain.com`

---

## 📊 Workflow File

The deployment is defined in: `.github/workflows/deploy.yml`

**What it does**:
1. Checks out code
2. Logs into Docker Hub (using token)
3. Builds Docker image with caching
4. Pushes to Docker Hub
5. SSHs to server and deploys
6. Tests health endpoint
7. Reports success/failure

**Triggers**:
- Automatic: Push to `main` branch
- Manual: GitHub Actions UI

---

## ✅ Checklist

### First Deployment
- [ ] Add all GitHub Secrets
- [ ] SSH to server and create Docker volumes
- [ ] Open firewall port 8080
- [ ] Push to `main` branch or trigger manual deployment
- [ ] Wait for GitHub Action to complete
- [ ] Test: `curl http://196.43.168.57:8080/health`
- [ ] Visit: http://196.43.168.57:8080/docs

### Every Deployment
- [ ] Make code changes
- [ ] Commit and push to `main`
- [ ] GitHub Actions deploys automatically
- [ ] Check Actions tab for status
- [ ] Test endpoints

---

## 🎯 Summary

**Deployment is fully automated!**

1. **Setup once**: Add GitHub Secrets, create Docker volumes
2. **Deploy**: Just push to `main` branch
3. **Monitor**: Check GitHub Actions tab
4. **Manage**: Use SSH commands when needed

No manual steps, no scripts to run, just push and deploy! 🚀

---

**New API URL**: `http://196.43.168.57:8080`  
**Replace**: `https://bsads-api-production.up.railway.app` with new URL in your apps.
