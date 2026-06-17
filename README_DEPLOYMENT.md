# BSADS API - Deployment Ready! 🚀

## 📦 What's Been Fixed

### ✅ Issue 1: Port Mapping (FIXED)
- FastAPI now properly exposed on port **8085**
- Added `-p 8085:8085` to Docker configuration

### ✅ Issue 2: Docker Networking (FIXED)
- Container can now reach simulation server on same host
- Added `--add-host=host.docker.internal:host-gateway`
- Automatic URL translation: `196.43.168.57` → `host.docker.internal`

### ✅ Issue 3: Laravel Database Access (NEW)
- PostgreSQL exposed on port **5433**
- Laravel can connect to the database
- Added `-p 5433:5432` to Docker configuration

---

## 🚀 Quick Deployment (Choose One)

### Option A: Automated (GitHub Actions) ⭐ RECOMMENDED
```bash
git add .
git commit -m "Deploy BSADS API with all fixes"
git push origin main
```
Then monitor at: https://github.com/YOUR_USERNAME/YOUR_REPO/actions

### Option B: Manual (Immediate)
```bash
# SSH to server
ssh ademneadev@196.43.168.57

# Run deployment script
bash expose_postgres.sh
```

---

## 📋 Files Created/Modified

### Core Fixes (Commit These)
- ✅ `api/http_connector.py` - URL translation for Docker
- ✅ `.github/workflows/deploy.yml` - Updated deployment with all fixes
- ✅ `Dockerfile.production` - Port 8085 configuration
- ✅ `.env.production` - PORT=8085
- ✅ `start_production.sh` - Default port 8085

### Deployment Scripts (Optional, for manual use)
- 📄 `expose_postgres.sh` - Deploy with PostgreSQL exposed
- 📄 `deploy_with_host_network.sh` - Alternative with host networking
- 📄 `diagnose_connection.sh` - Troubleshooting diagnostics
- 📄 `fix_docker_networking.sh` - Quick networking fix

### Documentation (Reference)
- 📚 `COMPLETE_DEPLOYMENT_GUIDE.md` - Full deployment guide ⭐
- 📚 `LARAVEL_DATABASE_ACCESS.md` - Laravel integration guide
- 📚 `TROUBLESHOOTING.md` - Common issues and solutions
- 📚 `DOCKER_NETWORKING_FIX.md` - Technical networking details
- 📚 `PRE_PUSH_CHECKLIST.md` - Pre-deployment checklist
- 📚 `QUICK_FIX_SUMMARY.md` - Quick reference

### Helper Files
- 📄 `update_server_url.sql` - SQL script to update URLs in database
- 📄 `COMMIT_MESSAGE.txt` - Suggested commit message

---

## 🎯 What You Need to Do NOW

### Step 1: Verify GitHub Secrets (IMPORTANT!)

Go to: **GitHub → Settings → Secrets and variables → Actions**

Ensure these exist:
- [x] `DOCKERHUB_USERNAME`
- [x] `DOCKERHUB_TOKEN`
- [x] `SERVER_PASSWORD`
- [x] `SECRET_KEY`
- [x] `HF_SPACE_NAME`
- [x] `HF_TOKEN`

### Step 2: Commit and Push

```bash
# Review changes
git status
git diff .github/workflows/deploy.yml
git diff api/http_connector.py

# Commit everything
git add .github/workflows/deploy.yml
git add api/http_connector.py
git add Dockerfile.production
git add .env.production
git add start_production.sh
git add redeploy_with_port_fix.sh

# Add documentation (optional but recommended)
git add *.md *.sh *.sql

# Commit
git commit -m "Fix Docker networking, port mapping, and expose PostgreSQL for Laravel

- Add port mapping for API (8085) and PostgreSQL (5433)
- Implement automatic URL translation for Docker networking
- Configure host.docker.internal gateway for same-host communication
- Enable Laravel database access via exposed PostgreSQL port

Fixes: Connection timeout issues and port accessibility"

# Push to trigger deployment
git push origin main  # or your branch name
```

### Step 3: Monitor Deployment

Watch GitHub Actions:
1. Go to your repo on GitHub
2. Click **Actions** tab
3. Watch the "Deploy to Production Server" workflow
4. Should complete in ~5-10 minutes

### Step 4: Verify Deployment

SSH to your server and test:

```bash
ssh ademneadev@196.43.168.57

# Test API
curl http://196.43.168.57:8085/health
# Expected: {"status":"ok","service":"BSADS API"}

# Check container
docker ps | grep bsads-api-production
# Should show ports: 8085->8085 and 5433->5432

# Check logs (should see URL translation)
docker logs bsads-api-production 2>&1 | grep -E "(Translating|Starting|Ready)"

# Test PostgreSQL from Laravel
psql -h 196.43.168.57 -p 5433 -U bee_user -d bee_db
# Password: bee_user
```

---

## 🔧 Laravel Configuration

### Update Your Laravel .env:

```env
DB_CONNECTION=pgsql
DB_HOST=196.43.168.57
DB_PORT=5433
DB_DATABASE=bee_db
DB_USERNAME=bee_user
DB_PASSWORD=bee_user
```

### Test in Laravel:

```bash
php artisan config:clear
php artisan tinker
>>> DB::connection()->getPdo();
>>> DB::select('SELECT COUNT(*) FROM users');
```

---

## 🐛 If Something Goes Wrong

### Simulation Server Connection Issues?

**Run diagnostics:**
```bash
ssh ademneadev@196.43.168.57
bash diagnose_connection.sh
```

**Quick fix (use host network):**
```bash
bash deploy_with_host_network.sh
```

### API Not Accessible?

**Check container:**
```bash
docker ps | grep bsads-api-production
docker logs -f bsads-api-production
```

**Redeploy:**
```bash
bash expose_postgres.sh
```

### Laravel Cannot Connect to Database?

**Check port is exposed:**
```bash
docker ps | grep 5433
```

**Allow firewall (if Laravel on different server):**
```bash
sudo ufw allow 5433/tcp
```

---

## 📊 Expected Behavior After Deployment

### ✅ API Health Check
```bash
curl http://196.43.168.57:8085/health
# Returns: {"status":"ok","service":"BSADS API"}
```

### ✅ Container Logs
```
🔄 Translating 196.43.168.57 → host.docker.internal (same-host detection)
✓ Discovery poller: completed scan
✓ Inference poller: no pending audio sources
```

### ✅ Hive Creation
```json
{
  "hive_id": "...",
  "folder_created": true,
  "folder_creation_error": null
}
```

### ✅ Laravel Database Access
```bash
psql -h 196.43.168.57 -p 5433 -U bee_user -d bee_db
# Successfully connected
```

---

## 🎉 Success Indicators

- [ ] GitHub Actions deployment completes successfully
- [ ] API responds at http://196.43.168.57:8085/health
- [ ] Container logs show URL translation working
- [ ] No timeout errors in logs
- [ ] Hive creation succeeds with `folder_created: true`
- [ ] Laravel can connect to database on port 5433
- [ ] PostgreSQL queries work from Laravel

---

## 📚 Key Documentation Files

| File | Purpose |
|------|---------|
| **COMPLETE_DEPLOYMENT_GUIDE.md** | 📖 Full deployment guide with all details |
| **LARAVEL_DATABASE_ACCESS.md** | 🔗 Laravel database integration |
| **TROUBLESHOOTING.md** | 🔧 Common issues and solutions |
| **diagnose_connection.sh** | 🔍 Diagnostic script |
| **expose_postgres.sh** | 🚀 Quick deployment script |

---

## 💡 Pro Tips

1. **Always check simulation server is running first:**
   ```bash
   curl http://localhost:8086/health
   ```

2. **Use diagnostics before asking for help:**
   ```bash
   bash diagnose_connection.sh
   ```

3. **Watch logs in real-time during testing:**
   ```bash
   docker logs -f bsads-api-production
   ```

4. **Backup database before major changes:**
   ```bash
   docker exec bsads-api-production pg_dump -U bee_user bee_db > backup.sql
   ```

---

## 🆘 Need Help?

1. ✅ Check **TROUBLESHOOTING.md**
2. ✅ Run `bash diagnose_connection.sh`
3. ✅ Check container logs: `docker logs -f bsads-api-production`
4. ✅ Review **COMPLETE_DEPLOYMENT_GUIDE.md**

---

## ✨ Summary

Everything is ready to deploy! Your codebase now includes:

- ✅ Fixed port mapping (8085 for API)
- ✅ Fixed Docker networking (host.docker.internal)
- ✅ PostgreSQL exposed (5433 for Laravel)
- ✅ Automatic URL translation
- ✅ Complete documentation
- ✅ Deployment scripts
- ✅ Diagnostic tools

**Just commit, push, and watch it deploy! 🚀**

```bash
git add .
git commit -m "Deploy BSADS API with all fixes"
git push origin main
```
