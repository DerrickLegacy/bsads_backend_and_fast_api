# 🔐 GitHub Secrets Configuration

Add these secrets to your GitHub repository for automated deployment.

**Location**: Repository → Settings → Secrets and variables → Actions → New repository secret

---

## ✅ Required Secrets

### 1. Docker Hub Authentication

| Secret Name | Value | Where to Get |
|------------|-------|--------------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username | [hub.docker.com](https://hub.docker.com) (free account) |
| `DOCKERHUB_TOKEN` | Docker Hub access token | Docker Hub → Account Settings → Security → [New Access Token](https://hub.docker.com/settings/security) |

**Purpose**: GitHub Actions uses this to push Docker images to your Docker Hub account.

---

### 2. Server Access

| Secret Name | Value |
|------------|-------|
| `SERVER_PASSWORD` | `Ademneadev@26` |

**Purpose**: SSH into your server to deploy the container.

---

### 3. Application Secrets

| Secret Name | Value | How to Generate |
|------------|-------|-----------------|
| `SECRET_KEY` | Random secure string | Run: `python3 -c "import secrets; print(secrets.token_hex(32))"` |

**Purpose**: JWT token signing for authentication.

---

### 4. HuggingFace (Required for Audio Classification)

| Secret Name | Value | Where to Get |
|------------|-------|--------------|
| `HF_SPACE_NAME` | `DerrickLegacy256/bee-audio-classifier` | Your HuggingFace Space name |
| `HF_TOKEN` | Your HuggingFace token | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

**Purpose**: Your app sends audio files to HuggingFace for inference/classification. This is how your bee audio detection works.

---

## ❌ NOT Required

These are **NOT** needed as GitHub secrets (they're defaults or optional):

- ❌ `DATABASE_URL` - Uses default in container: `postgresql://bee_user:bee_user@localhost:5432/bee_db`
- ❌ `POLL_INTERVAL_SECONDS` - Has default: 60
- ❌ `POLL_OFFSET_SECONDS` - Has default: 15
- ❌ `RECOVERY_INTERVAL_MINUTES` - Has default: 3
- ❌ `INFERENCE_TIMEOUT_SECONDS` - Has default: 240
- ❌ `UPLOAD_DIR` - Has default: "uploads"
- ❌ `OPENWEATHER_API_KEY` - Optional, only if you use OpenWeatherMap
- ❌ `HF_WRITE_TOKEN` - Only for CI/CD model training, not runtime
- ❌ `HF_MODEL_ID` - Only informational, not required

---

## 📋 Summary Checklist

Add these **5 secrets** to GitHub:

- [ ] `DOCKERHUB_USERNAME` - Your Docker Hub username
- [ ] `DOCKERHUB_TOKEN` - Docker Hub access token (not password!)
- [ ] `SERVER_PASSWORD` - `Ademneadev@26`
- [ ] `SECRET_KEY` - Generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- [ ] `HF_SPACE_NAME` - `DerrickLegacy256/bee-audio-classifier`
- [ ] `HF_TOKEN` - Your HuggingFace token

---

## 🎯 Why Each Secret is Needed

### Docker Hub Secrets
Without these, GitHub Actions can't push your built image to Docker Hub, so deployment fails.

### Server Password
Without this, GitHub Actions can't SSH into your server to deploy the container.

### SECRET_KEY
Your FastAPI app requires this for JWT authentication. Without it, login/auth won't work.

### HuggingFace Secrets
Your app's core functionality is audio classification. Without these:
- ❌ Can't send audio to HuggingFace for analysis
- ❌ Can't detect bee swarming/absconding
- ❌ App still runs but audio classification fails

---

## 🔧 How to Add Secrets

1. Go to your GitHub repository
2. Click **Settings** (top menu)
3. Click **Secrets and variables** (left sidebar)
4. Click **Actions**
5. Click **New repository secret** (green button)
6. Enter **Name** (exactly as shown above)
7. Enter **Value**
8. Click **Add secret**
9. Repeat for all 5 secrets

---

## ✅ Verify Secrets Added

After adding all secrets, go to:
**Settings → Secrets and variables → Actions → Repository secrets**

You should see:
- DOCKERHUB_USERNAME
- DOCKERHUB_TOKEN
- SERVER_PASSWORD
- SECRET_KEY
- HF_SPACE_NAME
- HF_TOKEN

**Total: 6 secrets**

---

## 🚀 Ready to Deploy

Once all secrets are added:
```bash
git push origin main
```

GitHub Actions will automatically deploy! 🎉
