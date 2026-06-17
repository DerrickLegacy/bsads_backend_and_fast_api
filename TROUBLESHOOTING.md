# Troubleshooting: Connection to host.docker.internal:8086 Timeout

## Current Status

✅ **Good News:** URL translation is working!
- Log shows: `🔄 Translating 196.43.168.57 → host.docker.internal`

❌ **Issue:** Container cannot reach `host.docker.internal:8086`
- Error: `Connection to host.docker.internal timed out (connect timeout=10)`

## Root Cause

The container is trying to connect to `host.docker.internal:8086` but timing out. This means **one of these issues**:

1. **Container doesn't have `--add-host` flag** (most likely)
2. **Simulation server is not running** on port 8086
3. **Firewall is blocking** container→host traffic
4. **Server is only listening on external IP**, not localhost

---

## Step 1: Run Diagnostics (REQUIRED)

SSH to your server and run the diagnostic script:

```bash
ssh ademneadev@196.43.168.57

# Download the diagnostic script (if not already there)
# Or copy the diagnose_connection.sh file to the server

bash diagnose_connection.sh
```

This will tell you exactly what's wrong.

---

## Step 2: Check if Simulation Server is Running

On your server, check if port 8086 is listening:

```bash
# Check what's listening on port 8086
sudo lsof -i :8086
# OR
sudo netstat -tulnp | grep 8086
# OR
sudo ss -tulnp | grep 8086

# Try to connect from the host
curl http://localhost:8086/health
```

**If nothing is listening on port 8086:**
- ❌ Your simulation server is **NOT running**
- Start it first before trying to use the API!

**If you see output:**
- ✅ Simulation server is running
- Note what IP it's bound to (0.0.0.0 is good, 196.43.168.57 only might be a problem)

---

## Step 3: Choose a Solution

### **Solution A: Host Network Mode** ⭐ RECOMMENDED (Simplest)

This is the easiest and most reliable solution on Linux when both services are on the same host.

**Advantages:**
- ✅ No complex networking configuration
- ✅ Container can access `localhost:8086` directly
- ✅ Works even if `--add-host` fails
- ✅ No URL translation needed

**Disadvantage:**
- ⚠️ Less network isolation (container shares host network)

**Deploy:**
```bash
ssh ademneadev@196.43.168.57
bash deploy_with_host_network.sh
```

**Update GitHub workflow** to use host network:
```yaml
docker run -d \
  --name ${{ env.CONTAINER_NAME }} \
  --restart unless-stopped \
  --network host \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e PORT=8085 \
  ...
```

---

### **Solution B: Fix host.docker.internal** (More Complex)

If you prefer isolated networking, verify the container has the `--add-host` flag:

```bash
# Check if flag was applied
docker inspect bsads-api-production --format '{{.HostConfig.ExtraHosts}}'

# Should output: [host.docker.internal:host-gateway]
# If empty: container was started without the flag!
```

**If missing, restart with the flag:**
```bash
docker stop bsads-api-production
docker rm bsads-api-production

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
```

**Then test from inside container:**
```bash
# Should work now
docker exec bsads-api-production curl -v http://host.docker.internal:8086/health
```

---

### **Solution C: Update User URL to localhost** (Quick Fix)

If the above don't work, update the database to use `localhost` instead:

```bash
docker exec -it bsads-api-production bash
psql $DATABASE_URL

UPDATE users 
SET server_url = 'http://localhost:8086/'
WHERE server_url = 'http://196.43.168.57:8086/';

\q
exit
```

This works with **host network mode** because the container shares the host's localhost.

---

## Step 4: Verify the Fix

After applying any solution:

```bash
# 1. Check API health
curl http://196.43.168.57:8085/health

# 2. Check container can reach simulation server
docker exec bsads-api-production curl http://localhost:8086/health
# OR (if using host.docker.internal)
docker exec bsads-api-production curl http://host.docker.internal:8086/health

# 3. Create a test hive
curl -X POST http://196.43.168.57:8085/bsads-api-db/hives \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "hive_name": "Test Hive",
    "hive_location": "Test",
    "hive_type": "Box",
    "installation_date": "2026-06-17",
    "latitude": 0.39,
    "longitude": 0.98,
    "owner_id": "YOUR_USER_ID"
  }'

# Should return: "folder_created": true

# 4. Watch logs - should show NO timeout errors
docker logs -f bsads-api-production
```

---

## Common Issues & Solutions

### Issue: "host.docker.internal: Name or service not known"

**Cause:** Container doesn't have `--add-host` configured

**Fix:** Restart container with `--add-host=host.docker.internal:host-gateway` OR use host network mode

---

### Issue: "Connection to host.docker.internal timed out"

**Possible causes:**
1. Simulation server not running → Start it first!
2. Firewall blocking traffic → Check `iptables` or use host network mode
3. Server bound to wrong IP → Ensure it listens on `0.0.0.0` or `localhost`

**Quick fix:** Use host network mode (Solution A)

---

### Issue: "Connection to localhost:8086 refused" (in host network mode)

**Cause:** Simulation server is not running

**Fix:** Start your simulation server on port 8086 first!

---

## Comparison: host.docker.internal vs Host Network

| Feature | `--add-host` (Bridge) | `--network host` |
|---------|----------------------|-------------------|
| Network Isolation | ✅ Isolated | ❌ Shared |
| Port Mapping | ✅ Needed (`-p`) | ❌ Not needed |
| Access host services | Via `host.docker.internal` | Via `localhost` |
| Complexity | 🟡 Medium | 🟢 Simple |
| Works on Linux | ⚠️ Sometimes fails | ✅ Always works |
| **Recommendation** | For public deployment | **For same-host development** ⭐ |

---

## Recommended Deployment Strategy

### For Development/Testing (same host):
```bash
--network host
```
Simplest, most reliable when both API and simulation are on same server.

### For Production (separate hosts):
```bash
--add-host=host.docker.internal:host-gateway -p 8085:8085
```
Better isolation, works when simulation server is on a different machine or using ngrok.

---

## Quick Commands Reference

```bash
# Check if simulation server is running
curl http://localhost:8086/health

# Check container networking
docker inspect bsads-api-production --format '{{.HostConfig.ExtraHosts}}'
docker inspect bsads-api-production --format '{{.HostConfig.NetworkMode}}'

# Test from inside container
docker exec bsads-api-production curl -v http://localhost:8086/health
docker exec bsads-api-production curl -v http://host.docker.internal:8086/health
docker exec bsads-api-production cat /etc/hosts | grep host.docker.internal

# Restart with host network (easiest fix)
docker stop bsads-api-production && docker rm bsads-api-production
bash deploy_with_host_network.sh

# View logs
docker logs -f bsads-api-production | grep -E "(Translating|timeout|Connection)"
```

---

## Summary

**Most likely issue:** Simulation server is not running on port 8086, OR container doesn't have `--add-host` flag.

**Fastest solution:** Use host network mode (`bash deploy_with_host_network.sh`)

**Check first:** Run `diagnose_connection.sh` to identify the exact problem.
