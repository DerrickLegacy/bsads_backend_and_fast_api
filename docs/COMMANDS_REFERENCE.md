# 📋 Quick Commands Reference

## 🚀 Deployment

### Automatic Deploy
```bash
git push origin main  # Triggers GitHub Actions automatically
```

### Manual Deploy
Go to GitHub → Actions → Deploy to Production Server → Run workflow

---

## 📊 Monitoring

### Health Check
```bash
curl http://196.43.168.57:8080/health
```

### Container Status
```bash
ssh ademneadev@196.43.168.57 'docker ps | grep bsads'
```

### View Logs
```bash
# Real-time
ssh ademneadev@196.43.168.57 'docker logs -f bsads-api-production'

# Last 100 lines
ssh ademneadev@196.43.168.57 'docker logs --tail 100 bsads-api-production'

# Search for errors
ssh ademneadev@196.43.168.57 'docker logs bsads-api-production 2>&1 | grep -i error'
```

### Supervisor Status
```bash
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production supervisorctl status'
```

---

## 🔧 Container Management

### Restart
```bash
ssh ademneadev@196.43.168.57 'docker restart bsads-api-production'
```

### Stop
```bash
ssh ademneadev@196.43.168.57 'docker stop bsads-api-production'
```

### Start
```bash
ssh ademneadev@196.43.168.57 'docker start bsads-api-production'
```

### Remove (⚠️ Data volumes persist)
```bash
ssh ademneadev@196.43.168.57 'docker rm -f bsads-api-production'
```

### Shell Access
```bash
ssh ademneadev@196.43.168.57 'docker exec -it bsads-api-production bash'
```

### Resource Usage
```bash
ssh ademneadev@196.43.168.57 'docker stats bsads-api-production --no-stream'
```

---

## 💾 Database

### Backup
```bash
# Simple backup
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production pg_dump -U bee_user bee_db' > backup-$(date +%Y%m%d).sql

# Compressed backup
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production pg_dump -U bee_user bee_db' | gzip > backup-$(date +%Y%m%d).sql.gz
```

### Restore
```bash
# From SQL file
cat backup.sql | ssh ademneadev@196.43.168.57 'docker exec -i bsads-api-production psql -U bee_user bee_db'

# From compressed
gunzip -c backup.sql.gz | ssh ademneadev@196.43.168.57 'docker exec -i bsads-api-production psql -U bee_user bee_db'
```

### Database Shell
```bash
ssh ademneadev@196.43.168.57 'docker exec -it bsads-api-production psql -U bee_user -d bee_db'
```

### Run Query
```bash
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production psql -U bee_user -d bee_db -c "SELECT COUNT(*) FROM hives;"'
```

### List Tables
```bash
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production psql -U bee_user -d bee_db -c "\dt"'
```

---

## 📦 Volume Management

### List Volumes
```bash
ssh ademneadev@196.43.168.57 'docker volume ls | grep bsads'
```

### Inspect Volume
```bash
ssh ademneadev@196.43.168.57 'docker volume inspect bsads-data'
```

### Backup Volume
```bash
ssh ademneadev@196.43.168.57 'docker run --rm -v bsads-data:/data -v $(pwd):/backup alpine tar czf /backup/bsads-data.tar.gz -C /data .'
```

---

## 🐛 Debugging

### Check Processes
```bash
# All processes
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production ps aux'

# FastAPI only
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production ps aux | grep uvicorn'

# PostgreSQL only
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production ps aux | grep postgres'
```

### Test API Internally
```bash
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production curl localhost:8080/health'
```

### Check Port Binding
```bash
ssh ademneadev@196.43.168.57 'sudo netstat -tulpn | grep 8080'
```

### Supervisor Logs
```bash
# FastAPI logs
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production tail -f /var/log/supervisor/fastapi.log'

# PostgreSQL logs
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production tail -f /var/log/supervisor/postgresql.log'

# Supervisor itself
ssh ademneadev@196.43.168.57 'docker exec bsads-api-production tail -f /var/log/supervisor/supervisord.log'
```

---

## 🔍 System Info

### Disk Space
```bash
ssh ademneadev@196.43.168.57 'df -h'
```

### Memory
```bash
ssh ademneadev@196.43.168.57 'free -h'
```

### Docker Disk Usage
```bash
ssh ademneadev@196.43.168.57 'docker system df'
```

---

## 🔥 Firewall

### Check Status
```bash
ssh ademneadev@196.43.168.57 'sudo ufw status'
```

### Open Port 8080
```bash
ssh ademneadev@196.43.168.57 'sudo ufw allow 8080/tcp'
```

---

## 🎯 Quick Actions

### Full Restart
```bash
ssh ademneadev@196.43.168.57 'docker restart bsads-api-production'
```

### Check Everything is Working
```bash
./test_deployment.sh
```

### View Recent Activity
```bash
ssh ademneadev@196.43.168.57 'docker logs --tail 50 bsads-api-production'
```

---

## 🌐 API URLs

| Endpoint | URL |
|----------|-----|
| Health | http://196.43.168.57:8080/health |
| API Docs | http://196.43.168.57:8080/docs |
| ReDoc | http://196.43.168.57:8080/redoc |
| OpenAPI | http://196.43.168.57:8080/openapi.json |

---

## 🔐 Server Access

```
Host: 196.43.168.57
User: ademneadev
SSH: ssh ademneadev@196.43.168.57
```
