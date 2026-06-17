# ⚡ Setup Summary - Automated Deployment

## 🎯 What You Need to Configure

### Step 1: Add GitHub Secrets (6 total)

Go to: **Your Repo → Settings → Secrets and variables → Actions → New repository secret**

| # | Secret Name | Value | Notes |
|---|-------------|-------|-------|
| 1 | `DOCKERHUB_USERNAME` | Your Docker Hub username | Get free account at hub.docker.com |
| 2 | `DOCKERHUB_TOKEN` | Your Docker Hub token | Generate at Docker Hub → Settings → Security |
| 3 | `SERVER_PASSWORD` | `Ademneadev@26` | Your server password |
| 4 | `SECRET_KEY` | Generate new one | Run: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| 5 | `HF_SPACE_NAME` | `DerrickLegacy256/bee-audio-classifier` | Your HuggingFace Space |
| 6 | `HF_TOKEN` | Your HF token | Get from huggingface.co/settings/tokens |

**Why these are needed:**
- **Docker Hub**: To store and deploy your app image
- **Server Password**: To SSH and deploy container
- **SECRET_KEY**: For JWT authentication in your API
- **HuggingFace**: For audio classification (core feature)

---

### Step 2: Setup Server (One-Time, 3 commands)

```bash
ssh ademneadev@196.43.168.57

# Create data volumes
docker volume create bsads-data
docker volume create bsads-uploads

# Open firewall
sudo ufw allow 8080/tcp

exit
```

**Why:** Creates persistent storage for database and uploads. Port 8080 must be open for API access.

---

### Step 3: Deploy

```bash
git push origin main
```

**That's it!** GitHub Actions automatically deploys.

---

## 📊 What Happens on Deploy

1. **GitHub Actions triggered** by push to `main`
2. **Builds Docker image** (PostgreSQL + FastAPI)
3. **Pushes to Docker Hub** using your credentials
4. **SSHs to server** using password
5. **Pulls image and deploys** new container
6. **Tests health endpoint** to verify
7. **Reports success/failure** in Actions tab

---

## 🌐 Your Deployed API

**URL**: http://196.43.168.57:8080
**Docs**: http://196.43.168.57:8080/docs

Replace `https://bsads-api-production.up.railway.app` with this in your apps.

---

## ❓ Why NOT Other Variables?

You might wonder why some variables from `.env.example` aren't in GitHub Secrets:

| Variable | Why NOT Needed |
|----------|----------------|
| `DATABASE_URL` | Hardcoded in container: `postgresql://bee_user:bee_user@localhost:5432/bee_db` |
| `POLL_INTERVAL_SECONDS` | Has default: 60 |
| `POLL_OFFSET_SECONDS` | Has default: 15 |
| `RESET_DATABASE` | Always false in production (safety) |
| `UPLOAD_DIR` | Has default: "uploads" |
| `OPENWEATHER_API_KEY` | Optional feature |
| `HF_WRITE_TOKEN` | Only for model training, not runtime |

**These have sensible defaults or are computed internally.**

---

## 🏗️ Architecture Explained

### Why Supervisor?
**Supervisor** is a process manager that runs inside the container. It:
- Starts PostgreSQL first, then FastAPI
- Monitors both processes
- Auto-restarts if either crashes
- Provides unified logging

### Why Single Container?
- Simpler deployment (one unit)
- No networking complexity
- Easier to manage
- Faster startup

### Data Persistence
Docker volumes (`bsads-data`, `bsads-uploads`) persist across:
- Container restarts
- Deployments
- Updates

Your data is safe! 🔒

---

## ✅ Verification

After first deployment:

```bash
# Check it's running
curl http://196.43.168.57:8080/health

# Should return:
# {"status":"ok","service":"BSADS API"}
```

Visit http://196.43.168.57:8080/docs to see interactive API docs.

---

## 🎉 That's Everything!

**Summary:**
1. Add 6 GitHub Secrets ← Do once
2. Create Docker volumes on server ← Do once
3. Push to `main` branch ← Every deploy

**Fully automated, no manual deployment scripts!**

---

## 📚 More Info

- **`GITHUB_SECRETS_REQUIRED.md`** - Detailed secrets explanation
- **`AUTOMATED_DEPLOYMENT.md`** - Complete automation guide
- **`COMMANDS_REFERENCE.md`** - Useful commands
- **`.github/workflows/deploy.yml`** - The actual workflow file
