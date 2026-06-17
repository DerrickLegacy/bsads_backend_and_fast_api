# Farmer Server Configuration Guide

## Overview

Farmers run their own data source servers that provide audio recordings to the BSADS API. The BSADS API polls these farmer servers periodically to discover and process new audio files.

## Architecture

```
┌─────────────────────────────────┐
│  BSADS API Server               │
│  (Central - Your Server)        │
│  - Polls farmer servers         │
│  - Processes audio              │
│  - Stores results               │
└─────────────────────────────────┘
           ↓ HTTP API calls
           ↓ (over internet)
┌─────────────────────────────────┐
│  Farmer's Server (Remote)       │
│  - Farmer's own machine         │
│  - Serves audio recordings      │
│  - Provides API key auth        │
└─────────────────────────────────┘
```

## Server URL Configuration

When configuring a farmer's `server_url`, the correct value depends on **where the farmer's server is running**:

### Scenario 1: Farmer on Different Server (Production - Most Common)

**Use:** Publicly accessible URL

Examples:
- **Ngrok**: `https://abc123-xyz789.ngrok-free.dev`
- **Public IP**: `http://45.67.89.123:5000`
- **Domain**: `https://farmer-api.example.com`

```sql
-- Example configuration
UPDATE users 
SET server_url = 'https://abc123-xyz789.ngrok-free.dev',
    api_key = 'f47ac10b-58cc-4372-a567-0e02b2c3d479'
WHERE email = 'farmer@example.com';
```

### Scenario 2: Testing with Both Services on Same Server

If you're running both BSADS API and farmer simulation on the **same physical server**:

#### Option A: Both in Docker Containers (Recommended)
**Use:** Container name + internal port

```sql
UPDATE users 
SET server_url = 'http://farmer-data-source:8000'
WHERE email = 'test-farmer@example.com';
```

**Note:** Use the **internal container port** (8000), not the host-mapped port (8086).

#### Option B: BSADS in Docker, Farmer on Host
**Use:** `host.docker.internal` (Docker 18.03+)

```sql
UPDATE users 
SET server_url = 'http://host.docker.internal:8086'
WHERE email = 'test-farmer@example.com';
```

#### Option C: Use Host Network Mode
Run BSADS container with `--network host`:

```bash
docker run --network host ...
```

Then use: `http://localhost:8086` or `http://196.43.168.57:8086`

### Scenario 3: Local Development

When developing locally (both services outside Docker):

```sql
UPDATE users 
SET server_url = 'http://localhost:5000'
WHERE email = 'dev-farmer@example.com';
```

## Common Issues

### ❌ Connection Timeout from Docker Container

**Symptom:**
```
ConnectTimeoutError: Connection to 196.43.168.57 timed out
```

**Cause:** Trying to reach host's public IP from inside Docker container

**Solutions:**
1. Use container name: `http://farmer-data-source:8000`
2. Use special DNS: `http://host.docker.internal:PORT`
3. Use external URL: `https://ngrok-url.ngrok-free.dev`

### ❌ Wrong Port Number

**Remember:**
- **Host port mapping**: `8086->8000` means port 8000 inside, 8086 outside
- **Container-to-container**: Use internal port (8000)
- **External access**: Use host port (8086)

### ❌ Missing API Key

**Symptom:**
```
401 Unauthorized
```

**Solution:** Ensure both `server_url` AND `api_key` are configured:
```sql
SELECT email, server_url, 
       CASE WHEN api_key IS NOT NULL THEN '✓ Configured' ELSE '✗ Missing' END as api_key_status
FROM users 
WHERE server_url IS NOT NULL;
```

## Testing Configuration

### 1. Test from BSADS Container

```bash
# SSH to server
ssh user@bsads-server

# Test from inside container
docker exec bsads-api-production curl -v http://farmer-data-source:8000/health

# Should return: {"status":"ok"}
```

### 2. Test from Outside

```bash
# From your local machine or any external client
curl http://196.43.168.57:8086/health

# Should return: {"status":"ok"}
```

### 3. Test with API Key

```bash
# Test authenticated endpoint
curl -H "X-API-Key: your-api-key-here" \
  http://196.43.168.57:8086/recordings
```

## Quick Reference Table

| Scenario | Container Location | Farmer Location | server_url Value |
|----------|-------------------|-----------------|------------------|
| Production | Your server (Docker) | Farmer's server | `https://farmer-ngrok.ngrok-free.dev` |
| Testing | Your server (Docker) | Same server (Docker) | `http://farmer-data-source:8000` |
| Testing | Your server (Docker) | Same server (host) | `http://host.docker.internal:8086` |
| Development | Localhost | Localhost | `http://localhost:5000` |

## Best Practices

1. ✅ **Use HTTPS** for production (ngrok provides this automatically)
2. ✅ **Test connection** before activating data source
3. ✅ **Use descriptive client names** when generating API keys
4. ✅ **Document the farmer's setup** (ngrok command, port, etc.)
5. ✅ **Monitor connection health** via admin dashboard

## Admin Diagnostic Endpoint

Check all configured data sources:

```bash
curl -H "Authorization: Bearer <admin-token>" \
  http://196.43.168.57:8085/admin/data-sources/status
```

This shows:
- Which farmers have data sources configured
- Current connection status
- Recent errors
- Last successful scan time

## Related Documentation

- `/docs/1.FARMER_API_KEY_SETUP.md` - Setting up farmer credentials
- `/docs/API.md` - API endpoint reference
- `check_data_sources.sh` - Diagnostic script for checking configurations
