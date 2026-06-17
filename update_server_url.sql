-- ══════════════════════════════════════════════════════════════════════════════
-- Quick fix: Update server URLs to use host.docker.internal
-- Run this inside the container: psql $DATABASE_URL -f update_server_url.sql
-- ══════════════════════════════════════════════════════════════════════════════

-- Show current server URLs
SELECT id, full_name, email, server_url 
FROM users 
WHERE server_url IS NOT NULL;

-- Update all local server URLs (196.43.168.57) to use host.docker.internal
UPDATE users 
SET server_url = REPLACE(server_url, 'http://196.43.168.57:', 'http://host.docker.internal:')
WHERE server_url LIKE 'http://196.43.168.57:%';

-- Show updated URLs
SELECT id, full_name, email, server_url 
FROM users 
WHERE server_url IS NOT NULL;

-- Verify the change
SELECT 
  CASE 
    WHEN server_url LIKE '%host.docker.internal%' THEN '✅ Updated correctly'
    WHEN server_url LIKE '%196.43.168.57%' THEN '❌ Still using old URL'
    ELSE '⚠️ Other URL format'
  END AS status,
  full_name,
  server_url
FROM users
WHERE server_url IS NOT NULL;
