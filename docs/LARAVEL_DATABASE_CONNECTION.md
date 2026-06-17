# 🔌 Laravel Admin Dashboard - Database Connection Guide

Your Laravel admin dashboard can connect directly to the PostgreSQL database.

---

## 📊 Connection Details

| Parameter | Value |
|-----------|-------|
| **Host** | `196.43.168.57` |
| **Port** | `5433` |
| **Database** | `bee_db` |
| **Username** | `bee_user` |
| **Password** | `bee_user` |

---

## ⚙️ Laravel Configuration

### 1. Update `.env` File

```env
DB_CONNECTION=pgsql
DB_HOST=196.43.168.57
DB_PORT=5433
DB_DATABASE=bee_db
DB_USERNAME=bee_user
DB_PASSWORD=bee_user
```

### 2. Update `config/database.php`

Ensure PostgreSQL is configured:

```php
'connections' => [
    'pgsql' => [
        'driver' => 'pgsql',
        'host' => env('DB_HOST', '196.43.168.57'),
        'port' => env('DB_PORT', '5433'),
        'database' => env('DB_DATABASE', 'bee_db'),
        'username' => env('DB_USERNAME', 'bee_user'),
        'password' => env('DB_PASSWORD', 'bee_user'),
        'charset' => 'utf8',
        'prefix' => '',
        'schema' => 'public',
        'sslmode' => 'prefer',
    ],
],
```

### 3. Test Connection

```bash
php artisan migrate:status
```

If successful, you'll see the database tables!

---

## 🛡️ Security Note

**⚠️ The database password is weak for development.**

For production, you should:
1. Change the database password
2. Use SSL/TLS for database connections
3. Restrict database access by IP (firewall rules)

---

## 🔥 Open Firewall Port (If Needed)

If you can't connect, ensure port 5433 is open on the server:

```bash
ssh ademneadev@196.43.168.57
sudo ufw allow 5433/tcp
sudo ufw status
```

---

## 🧪 Test Connection from Command Line

```bash
# Using psql
psql postgresql://bee_user:bee_user@196.43.168.57:5433/bee_db

# Or with separate parameters
psql -h 196.43.168.57 -p 5433 -U bee_user -d bee_db
```

Password: `bee_user`

---

## 📊 Database Tables

Your Laravel dashboard can access all tables:

- `users` - System users
- `hives` - Beehive records
- `audio_sources` - Audio file metadata
- `inferences` - Classification results
- `alerts` - Generated alerts
- `advisory_templates` - Advisory templates
- `advisory_actions` - Advisory action items
- And more...

---

## 🔄 Connection String Format

Full connection string:
```
postgresql://bee_user:bee_user@196.43.168.57:5433/bee_db
```

---

## ❓ Troubleshooting

### Can't Connect

**1. Check if port is exposed:**
```bash
ssh ademneadev@196.43.168.57 'docker ps | grep bsads'
```

Look for: `-p 5433:5432`

**2. Check firewall:**
```bash
ssh ademneadev@196.43.168.57 'sudo ufw status | grep 5433'
```

Should show: `5433/tcp ALLOW Anywhere`

**3. Test from server:**
```bash
ssh ademneadev@196.43.168.57
docker exec -it bsads-api-production psql -U bee_user -d bee_db -c "SELECT 1"
```

### Connection Timeout

- Ensure firewall allows port 5432
- Check if container is running
- Verify network connectivity

### Authentication Failed

- Verify username: `bee_user`
- Verify password: `bee_user`
- Check database name: `bee_db`

---

## 🎯 Summary

Your Laravel admin dashboard connects directly to PostgreSQL at:

**Connection URL**: `postgresql://bee_user:bee_user@196.43.168.57:5433/bee_db`

**Exposed Ports**:
- Port 8085: FastAPI (for mobile/web apps)
- Port 5433: PostgreSQL (for Laravel admin only)

This gives your Laravel dashboard full database access while mobile/web apps use the secure API!
