# Laravel App → PostgreSQL Database Access

## Current Setup

Your PostgreSQL database is running **inside the Docker container** and is currently **not accessible** from outside. The container only exposes port **8085** (FastAPI), but PostgreSQL runs on port **5432** internally.

## Solution: Expose PostgreSQL Port

You have **two options** depending on your deployment mode:

---

## Option 1: Expose PostgreSQL Port (Bridge Network Mode)

If using normal Docker networking with port mapping:

### Step 1: Update Docker Run Command

Add `-p 5433:5432` to expose PostgreSQL:

```bash
docker stop bsads-api-production
docker rm bsads-api-production

docker run -d \
  --name bsads-api-production \
  --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  -p 8085:8085 \
  -p 5433:5432 \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="your-secret-key" \
  -e HF_SPACE_NAME="DerrickLegacy256/bee-audio-classifier" \
  -e HF_TOKEN="your-hf-token" \
  -e PORT=8085 \
  bsads2026/bsads-api:latest
```

**Note:** We use port **5433** on the host to avoid conflicts with any system PostgreSQL on port 5432.

### Step 2: Configure Laravel .env

In your Laravel project's `.env` file:

```env
DB_CONNECTION=pgsql
DB_HOST=196.43.168.57
DB_PORT=5433
DB_DATABASE=bee_db
DB_USERNAME=bee_user
DB_PASSWORD=bee_user
```

### Step 3: Test Connection

```bash
# From Laravel server, test the connection
psql -h 196.43.168.57 -p 5433 -U bee_user -d bee_db
# Password: bee_user

# Or use Laravel tinker
php artisan tinker
>>> DB::connection()->getPdo();
```

---

## Option 2: Host Network Mode (Simpler)

If using host network mode (recommended for same-host deployment):

### Step 1: Deploy with Host Network

```bash
docker stop bsads-api-production
docker rm bsads-api-production

docker run -d \
  --name bsads-api-production \
  --restart unless-stopped \
  --network host \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="your-secret-key" \
  -e HF_SPACE_NAME="DerrickLegacy256/bee-audio-classifier" \
  -e HF_TOKEN="your-hf-token" \
  -e PORT=8085 \
  bsads2026/bsads-api:latest
```

**Important:** PostgreSQL will listen on the **default port 5432** on the host.

### Step 2: Update PostgreSQL to Listen on All Interfaces

Inside the container, PostgreSQL needs to accept external connections:

```bash
# Connect to container
docker exec -it bsads-api-production bash

# Find PostgreSQL version
PG_VERSION=$(ls /usr/lib/postgresql/ | head -n1)
PG_DATA=/var/lib/postgresql/$PG_VERSION/main

# Already configured in Dockerfile, but verify:
cat $PG_DATA/postgresql.conf | grep listen_addresses
# Should show: listen_addresses='*'

cat $PG_DATA/pg_hba.conf | grep "0.0.0.0/0"
# Should show: host all all 0.0.0.0/0 md5

# Restart PostgreSQL if needed
supervisorctl restart postgresql
```

### Step 3: Configure Laravel .env

```env
DB_CONNECTION=pgsql
DB_HOST=196.43.168.57
DB_PORT=5432
DB_DATABASE=bee_db
DB_USERNAME=bee_user
DB_PASSWORD=bee_user
```

---

## Option 3: Different PostgreSQL Port (Avoid Conflicts)

If you have another PostgreSQL instance on the host, change the container's PostgreSQL port:

### Update Dockerfile.production

Add port configuration before starting PostgreSQL:

```dockerfile
# Change PostgreSQL port to 5434 to avoid conflicts
RUN sed -i 's/#port = 5432/port = 5434/' /var/lib/postgresql/*/main/postgresql.conf
```

Then expose it:
```bash
docker run -d ... -p 5434:5434 ...
```

And update Laravel:
```env
DB_PORT=5434
```

---

## Recommended Approach

### For Same-Host Deployment (API + Laravel on same server):

**Use Host Network Mode** (Option 2):
- ✅ Simplest setup
- ✅ PostgreSQL on default port 5432
- ✅ No port mapping needed
- ✅ Both containers can communicate easily

### For Separate Servers (Laravel on different server):

**Expose PostgreSQL Port** (Option 1):
- ✅ Use port 5433 to avoid conflicts
- ✅ Better security isolation
- ✅ Add `-p 5433:5432` to docker run

---

## Security Considerations

### 1. Firewall Rules

If Laravel is on a **different server**, open port 5433 (or 5432):

```bash
# Allow PostgreSQL access from Laravel server IP
sudo ufw allow from LARAVEL_SERVER_IP to any port 5433 proto tcp

# Or allow from anywhere (less secure)
sudo ufw allow 5433/tcp
```

### 2. PostgreSQL Authentication

The database currently uses `md5` authentication with password `bee_user`. For production:

**Option A: Keep current setup** (simple but less secure)
- Username: `bee_user`
- Password: `bee_user`
- Works fine for internal apps

**Option B: Create a separate Laravel user** (more secure)

```bash
docker exec -it bsads-api-production bash
su - postgres
psql

-- Create Laravel-specific user with read-only or limited access
CREATE USER laravel_user WITH PASSWORD 'strong_password_here';

-- Grant appropriate permissions
GRANT CONNECT ON DATABASE bee_db TO laravel_user;
\c bee_db
GRANT USAGE ON SCHEMA public TO laravel_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO laravel_user;

-- If Laravel needs write access to specific tables:
GRANT INSERT, UPDATE, DELETE ON specific_table TO laravel_user;

\q
exit
```

Then in Laravel `.env`:
```env
DB_USERNAME=laravel_user
DB_PASSWORD=strong_password_here
```

### 3. SSL/TLS Connection (Production)

For production, consider requiring SSL:

```bash
# In pg_hba.conf, change 'md5' to 'scram-sha-256' for better security
hostssl all all 0.0.0.0/0 scram-sha-256
```

And in Laravel `.env`:
```env
DB_SSLMODE=require
```

---

## Quick Setup Scripts

### Script 1: Expose PostgreSQL (Bridge Mode)

```bash
#!/bin/bash
# expose_postgres.sh

docker stop bsads-api-production
docker rm bsads-api-production

docker run -d \
  --name bsads-api-production \
  --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  -p 8085:8085 \
  -p 5433:5432 \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="${SECRET_KEY}" \
  -e HF_SPACE_NAME="${HF_SPACE_NAME}" \
  -e HF_TOKEN="${HF_TOKEN}" \
  -e PORT=8085 \
  bsads2026/bsads-api:latest

echo ""
echo "✅ PostgreSQL exposed on port 5433"
echo ""
echo "Laravel .env configuration:"
echo "DB_HOST=196.43.168.57"
echo "DB_PORT=5433"
echo "DB_DATABASE=bee_db"
echo "DB_USERNAME=bee_user"
echo "DB_PASSWORD=bee_user"
```

### Script 2: Test Connection from Laravel

```bash
#!/bin/bash
# test_db_connection.sh

echo "Testing PostgreSQL connection..."
psql -h 196.43.168.57 -p 5433 -U bee_user -d bee_db -c "SELECT version();"

if [ $? -eq 0 ]; then
    echo "✅ Connection successful!"
else
    echo "❌ Connection failed!"
    echo ""
    echo "Check:"
    echo "1. Is port 5433 exposed? docker ps"
    echo "2. Is firewall blocking? sudo ufw status"
    echo "3. Can you telnet? telnet 196.43.168.57 5433"
fi
```

---

## Laravel Database Configuration

### config/database.php

Make sure your PostgreSQL configuration is correct:

```php
'pgsql' => [
    'driver' => 'pgsql',
    'url' => env('DATABASE_URL'),
    'host' => env('DB_HOST', '127.0.0.1'),
    'port' => env('DB_PORT', '5432'),
    'database' => env('DB_DATABASE', 'forge'),
    'username' => env('DB_USERNAME', 'forge'),
    'password' => env('DB_PASSWORD', ''),
    'charset' => 'utf8',
    'prefix' => '',
    'prefix_indexes' => true,
    'search_path' => 'public',
    'sslmode' => 'prefer',
],
```

### Test in Laravel

```bash
# Clear config cache
php artisan config:clear

# Test connection
php artisan tinker
>>> DB::connection()->getPdo();
>>> DB::select('SELECT version()');

# Run migrations (if needed)
php artisan migrate

# Check tables
php artisan db:show
php artisan db:table users
```

---

## Troubleshooting

### Connection Refused

```bash
# Check if port is exposed
docker ps | grep bsads-api-production
# Should show: 0.0.0.0:5433->5432/tcp

# Check if PostgreSQL is running
docker exec bsads-api-production supervisorctl status postgresql
# Should show: RUNNING

# Check if port is accessible
telnet 196.43.168.57 5433
# Should connect
```

### Authentication Failed

```bash
# Verify credentials
docker exec -it bsads-api-production psql -U bee_user -d bee_db
# Should work with password: bee_user

# Check pg_hba.conf
docker exec bsads-api-production cat /var/lib/postgresql/*/main/pg_hba.conf
# Should have: host all all 0.0.0.0/0 md5
```

### Firewall Blocking

```bash
# Check firewall status
sudo ufw status

# Allow PostgreSQL port
sudo ufw allow 5433/tcp

# Or allow from specific IP
sudo ufw allow from LARAVEL_IP to any port 5433
```

---

## Summary

**Recommended Setup for Same-Host:**
1. Use host network mode: `--network host`
2. Laravel connects to: `196.43.168.57:5432`
3. Simplest and most reliable

**Recommended Setup for Different Servers:**
1. Add port mapping: `-p 5433:5432`
2. Laravel connects to: `196.43.168.57:5433`
3. Configure firewall to allow access

**Database Credentials:**
- Host: `196.43.168.57`
- Port: `5433` (bridge) or `5432` (host network)
- Database: `bee_db`
- Username: `bee_user`
- Password: `bee_user`

Your PostgreSQL database will be accessible to Laravel while remaining in the same container as your FastAPI application! 🚀
