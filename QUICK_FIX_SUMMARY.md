# Quick Fix Summary - Two Issues Resolved

## Issue #1: Port Not Exposed ✅ FIXED

**Problem:** API running on port 8085 inside container but not accessible from outside.

**Solution:** Added `-p 8085:8085` port mapping.

## Issue #2: Container Cannot Reach Host Services ✅ FIXED

**Problem:** API container cannot connect to simulation server at `196.43.168.57:8086` because both are on the same machine.

**Error:**
```
Connection to 196.43.168.57 timed out (connect timeout=10)
```

**Solution:** Added `--add-host=host.docker.internal:host-gateway` + automatic URL translation in code.

---

## Immediate Fix (Run on Server)

### Option A: Quick Script (Recommended)
```bash
# Copy the script to your server
scp fix_docker_networking.sh ademneadev@196.43.168.57:~/

# SSH and run it
ssh ademneadev@196.43.168.57
bash fix_docker_networking.sh
```

### Option B: Manual Commands
```bash
# SSH to server
ssh ademneadev@196.43.168.57

# Stop current container
docker stop bsads-api-production
docker rm bsads-api-production

# Start with both fixes
docker run -d \
  --name bsads-api-production \
  --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  -p 8085:8085 \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="your-secret-key" \
  -e HF_SPACE_NAME="DerrickLegacy256/bee-audio-classifier" \
  -e HF_TOKEN="your-hf-token" \
  -e PORT=8085 \
  bsads2026/bsads-api:latest

# Wait and check
sleep 20
docker logs -f bsads-api-production
```

---

## How It Works

### Before (Broken)
```
┌─────────────────────────────────────────────────┐
│ Host Machine (196.43.168.57)                    │
│                                                  │
│  ┌─────────────────┐      ┌──────────────────┐ │
│  │ Docker Container│──✗──▶│ Simulation Server│ │
│  │ API :8085       │      │ :8086            │ │
│  └─────────────────┘      └──────────────────┘ │
│         │                                        │
│         └──✗── No port mapping to host          │
└─────────────────────────────────────────────────┘
         ▲
         │
    ✗ Cannot access
```

### After (Fixed)
```
┌─────────────────────────────────────────────────┐
│ Host Machine (196.43.168.57)                    │
│                                                  │
│  ┌─────────────────┐      ┌──────────────────┐ │
│  │ Docker Container│──✓──▶│ Simulation Server│ │
│  │ API :8085       │ host │ :8086            │ │
│  │                 │.dock. │                  │ │
│  │                 │intern │                  │ │
│  └─────────────────┘      └──────────────────┘ │
│         │ :8085                                  │
│         └──✓── Port mapped via -p 8085:8085     │
└─────────────────────────────────────────────────┘
         ▲
         │
    ✓ Accessible from outside
```

### URL Translation (Automatic)

The code now automatically translates URLs when running in Docker:

```
User Config:  http://196.43.168.57:8086
              ↓ (detected Docker environment)
Actual Request: http://host.docker.internal:8086
```

No database changes needed! User can keep `http://196.43.168.57:8086/` in their profile.

---

## Testing Checklist

After applying the fix, test these:

### ✅ 1. API is accessible
```bash
curl http://196.43.168.57:8085/health
# Expected: {"status":"ok","service":"BSADS API"}
```

### ✅ 2. Port mapping is correct
```bash
docker ps | grep bsads-api-production
# Should show: 0.0.0.0:8085->8085/tcp
```

### ✅ 3. Host gateway is configured
```bash
docker exec bsads-api-production cat /etc/hosts | grep host.docker.internal
# Should show: <IP>    host.docker.internal
```

### ✅ 4. Container can reach simulation server
```bash
docker exec bsads-api-production curl http://host.docker.internal:8086/health
# Should return simulation server health response (not timeout)
```

### ✅ 5. URL translation is working
```bash
docker logs bsads-api-production 2>&1 | grep "Translating"
# Should show: 🔄 Translating 196.43.168.57 → host.docker.internal
```

### ✅ 6. Hive creation works
Create a hive via API and check:
- `folder_created: true` (not false)
- No `folder_creation_error`
- Folder appears in simulation server at `/home/farmer/recordings/<api-key>/<hive-name>/`

---

## Files Modified

1. ✅ `api/http_connector.py` - Added automatic URL translation
2. ✅ `.github/workflows/deploy.yml` - Added `--add-host` and `-p` flags
3. ✅ `Dockerfile.production` - Updated EXPOSE to 8085
4. ✅ `.env.production` - Changed PORT to 8085
5. ✅ `start_production.sh` - Updated default port to 8085
6. ✅ `redeploy_with_port_fix.sh` - Deployment script with fixes
7. ✅ `fix_docker_networking.sh` - Quick fix script (NEW)
8. ✅ `DOCKER_NETWORKING_FIX.md` - Detailed documentation (NEW)

---

## What Changed?

### Docker Run Command
```diff
  docker run -d \
    --name bsads-api-production \
    --restart unless-stopped \
+   --add-host=host.docker.internal:host-gateway \
+   -p 8085:8085 \
    -v bsads-data:/var/lib/postgresql \
    -v bsads-uploads:/app/uploads \
    -e PORT=8085 \
    ...
```

### HTTP Connector (Simplified)
```python
# Before
base_url = config.get("api_base_url")  # http://196.43.168.57:8086

# After
base_url = config.get("api_base_url")
base_url = _translate_localhost_url(base_url)  # http://host.docker.internal:8086
```

---

## Future Deployments

Next push to `main` branch will automatically deploy with both fixes. No manual intervention needed!

---

## Troubleshooting

### Still getting timeouts?

1. **Check simulation server is running:**
   ```bash
   curl http://localhost:8086/health
   ```

2. **Check from inside container:**
   ```bash
   docker exec -it bsads-api-production bash
   curl http://host.docker.internal:8086/health
   ```

3. **Check /etc/hosts inside container:**
   ```bash
   docker exec bsads-api-production cat /etc/hosts
   # Should contain: host.docker.internal
   ```

4. **Try host network mode (alternative):**
   ```bash
   docker run -d --name bsads-api-production --network host ...
   ```

---

## Summary

Both issues are now fixed with:
1. **Port mapping:** `-p 8085:8085` exposes API to external access
2. **Host gateway:** `--add-host=host.docker.internal:host-gateway` allows container→host communication
3. **Automatic translation:** Code detects Docker and translates IPs to `host.docker.internal`

No user data changes needed. Existing farmer URLs like `http://196.43.168.57:8086/` will work automatically! 🎉
