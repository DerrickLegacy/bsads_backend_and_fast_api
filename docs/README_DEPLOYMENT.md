# 🐝 BSADS API - Automated Deployment

**Fully automated deployment to your production server via GitHub Actions**

---

## 🎯 Quick Start

### 1. Add GitHub Secrets

Repository → Settings → Secrets and variables → Actions

```
DOCKERHUB_USERNAME     # Your Docker Hub username
DOCKERHUB_TOKEN        # Docker Hub access token
SERVER_PASSWORD        # Ademneadev@26
DATABASE_URL           # postgresql://bee_user:bee_user@localhost:5432/bee_db
SECRET_KEY             # Generate new: python3 -c "import secrets; print(secrets.token_hex(32))"
HF_SPACE_NAME          # DerrickLegacy256/bee-audio-classifier
HF_TOKEN               # Your HuggingFace token
```

### 2. Setup Server (One-Time)

```bash
ssh ademneadev@196.43.168.57
docker volume create bsads-data
docker volume create bsads-uploads
sudo ufw allow 8080/tcp
exit
```

### 3. Deploy

```bash
git push origin main  # Automatic deployment!
```

**Done!** API is live at: http://196.43.168.57:8080

---

## 🏗️ What's Inside

### Architecture
- **Single Docker container** with PostgreSQL + FastAPI
- **Supervisor** manages both processes (auto-restart, startup order, logging)
- **Docker volumes** for data persistence
- **Port 8080** exposed to internet

### Automated Workflow
1. Push code → GitHub Actions triggered
2. Build Docker image → Push to Docker Hub
3. SSH to server → Pull image → Deploy
4. Health check → Report status

---

## 📊 Monitor & Manage

### View Deployment
```bash
# GitHub Actions tab shows status
# Or check logs:
ssh ademneadev@196.43.168.57 'docker logs -f bsads-api-production'
```

### Quick Commands
```bash
# Restart
ssh ademneadev@196.43.168.57 'docker restart bsads-api-production'

# Status
ssh ademneadev@196.43.168.57 'docker ps | grep bsads'

# Health
curl http://196.43.168.57:8080/health
```

---

## 📚 Documentation

- **`AUTOMATED_DEPLOYMENT.md`** - Complete automation guide
- **`DEPLOYMENT_README.md`** - Overview and quick reference  
- **`COMMANDS_REFERENCE.md`** - All commands in one place

---

## ❓ FAQ

**Q: What is Supervisor?**  
A: Process manager that keeps PostgreSQL and FastAPI running in the container. Auto-restarts if they crash.

**Q: Why single container?**  
A: Simpler deployment, easier management, no networking complexity.

**Q: Is my data safe during updates?**  
A: Yes! Data stored in Docker volumes (`bsads-data`, `bsads-uploads`) persists across deployments.

**Q: How do I rollback?**  
A: Push previous commit to `main` branch or manually trigger workflow with old code.

**Q: Manual deployment?**  
A: No manual scripts needed! Just use GitHub Actions tab → Run workflow.

---

## 🎉 That's It!

Push to `main` → Automatic deployment → Live API

**API URL**: http://196.43.168.57:8080  
**API Docs**: http://196.43.168.57:8080/docs

Replace `https://bsads-api-production.up.railway.app` with new URL in your apps!
