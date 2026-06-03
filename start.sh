#!/bin/sh
set -e

echo "Running database migrations..."

# Railway uses lowercase database_url, handle both cases
DB_URL="${database_url:-${DATABASE_URL:-$POSTGRES_URL}}"

if [ -n "$DB_URL" ]; then
    echo "Database URL found, applying migrations..."
    
    echo "Applying user credentials migration..."
    if psql "$DB_URL" -f migrations/add_user_server_credentials.sql 2>&1; then
        echo "✓ User credentials migration applied successfully"
    else
        echo "⚠ User credentials migration skipped or failed (may already be applied)"
    fi
    
    echo "Applying soft delete migration..."
    if psql "$DB_URL" -f migrations/add_soft_delete_to_hives.sql 2>&1; then
        echo "✓ Soft delete migration applied successfully"
    else
        echo "⚠ Soft delete migration skipped or failed (may already be applied)"
    fi
else
    echo "⚠ WARNING: No database URL found. Skipping migrations."
    echo "Checked variables: database_url, DATABASE_URL, POSTGRES_URL"
fi

echo "Starting application..."
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
