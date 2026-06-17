# 🖥️ Server Setup Commands

Run these commands **once** on your server before first deployment.

---

## SSH into Server

```bash
ssh ademneadev@196.43.168.57
```

Password: `Ademneadev@26`

---

## 1. Create Docker Volumes

```bash
# Create volume for PostgreSQL data
docker volume create bsads-data

# Create volume for uploaded audio files
docker volume create bsads-uploads

# Verify volumes created
docker volume ls | grep bsads
```

**Expected output:**
```
local     bsads-data
local     bsads-uploads
```

---

## 2. Open Firewall Port

```bash
# Open port 8085 for API access
sudo ufw allow 8085/tcp

# Check firewall status
sudo ufw status
```

**Expected output:**
```
8080/tcp                   ALLOW       Anywhere
```

---

## 3. Verify Docker is Running

```bash
# Check Docker is installed and running
docker --version
docker ps
```

---

## 4. That's It!

Exit the server:
```bash
exit
```

Now push to `main` branch and GitHub Actions will deploy automatically!

---

## 📍 Note About Working Directory

The folder `~/bsads-api-db` on your server doesn't matter for deployment. Docker volumes are stored in Docker's managed storage (usually `/var/lib/docker/volumes/`), not in your home directory.

When you deploy:
- Container runs from Docker's image storage
- Data is stored in Docker volumes (`bsads-data`, `bsads-uploads`)
- You don't need any project files on the server!

---

## ✅ Verification Checklist

After deployment completes:

```bash
ssh ademneadev@196.43.168.57

# Check container is running
docker ps | grep bsads

# Check logs
docker logs bsads-api-production

# Test API
curl http://localhost:8080/health

exit
```

Then test from your local machine:
```bash
curl http://196.43.168.57:8080/health
```

---

## 🎯 Summary

**On Server (one-time):**
1. ✅ Create Docker volumes: `docker volume create bsads-data bsads-uploads`
2. ✅ Open firewall: `sudo ufw allow 8080/tcp`

**That's all!** GitHub Actions handles everything else.

No need for project files on the server - the container is self-contained!
