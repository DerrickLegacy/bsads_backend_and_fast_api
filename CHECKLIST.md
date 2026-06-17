# ✅ Deployment Checklist

## 📋 One-Time Setup

### GitHub Secrets (Add all 6)
- [ ] `DOCKERHUB_USERNAME` - Your Docker Hub username
- [ ] `DOCKERHUB_TOKEN` - Docker Hub access token (not password!)
- [ ] `SERVER_PASSWORD` - `Ademneadev@26`
- [ ] `SECRET_KEY` - Generate: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- [ ] `HF_SPACE_NAME` - `DerrickLegacy256/bee-audio-classifier`
- [ ] `HF_TOKEN` - Your HuggingFace token

**Where**: Repo → Settings → Secrets and variables → Actions

---

### Server Setup (Run once via SSH)
```bash
ssh ademneadev@196.43.168.57
docker volume create bsads-data
docker volume create bsads-uploads
sudo ufw allow 8080/tcp
exit
```

- [ ] Created `bsads-data` volume
- [ ] Created `bsads-uploads` volume
- [ ] Opened port 8080

---

## 🚀 Deploy

- [ ] Push to `main` branch: `git push origin main`
- [ ] Check GitHub Actions tab for status
- [ ] Wait for deployment to complete (~5-10 minutes)

---

## ✅ Verify Deployment

- [ ] Visit: http://196.43.168.57:8080/health
- [ ] Visit: http://196.43.168.57:8080/docs
- [ ] Test an API endpoint in the docs

---

## 🎉 Done!

Your API is live at **http://196.43.168.57:8080**

Replace `https://bsads-api-production.up.railway.app` in your apps with new URL.

---

## 📝 Notes

- **Deployment is automatic** - Just push to `main`
- **Data persists** - Database and uploads safe across deployments
- **Monitor via GitHub Actions** - Check Actions tab for logs
- **No manual scripts** - Everything via GitHub Actions

---

## 🆘 If Something Fails

1. Check GitHub Actions logs (Actions tab)
2. Verify all 6 secrets are added correctly
3. Ensure server volumes are created
4. Check port 8080 is open: `ssh ademneadev@196.43.168.57 'sudo ufw status'`

See `COMMANDS_REFERENCE.md` for debugging commands.
