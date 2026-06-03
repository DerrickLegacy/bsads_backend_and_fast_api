#!/bin/sh
set -e

echo "Running database migrations..."

# Run migrations if POSTGRES_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "Applying user credentials migration..."
    psql "$DATABASE_URL" -f migrations/add_user_server_credentials.sql || echo "Migration already applied or failed"
    
    echo "Applying soft delete migration..."
    psql "$DATABASE_URL" -f migrations/add_soft_delete_to_hives.sql || echo "Migration already applied or failed"
fi

echo "Starting application..."
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
