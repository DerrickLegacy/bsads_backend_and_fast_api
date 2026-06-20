#!/bin/bash
set -e

echo "============================================================"
echo "🐝 BSADS API - Production Container Starting"
echo "============================================================"

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until pg_isready -h localhost -U bee_user -d bee_db; do
    echo "   Waiting for database..."
    sleep 2
done
echo "✓ PostgreSQL is ready"

# Set database URL for migrations and app
export DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db"
export database_url="$DATABASE_URL"

echo ""
echo "📊 Environment Check:"
echo "  PORT: 8085"
echo "  DATABASE: postgresql://bee_user:***@localhost:5432/bee_db"
echo ""

echo "🔄 Running database migrations..."

echo ""
echo "📝 Applying user credentials migration..."
if psql "$DATABASE_URL" -f migrations/add_user_server_credentials.sql 2>&1 | grep -v "^$"; then
    echo "✓ User credentials migration completed"
fi

echo ""
echo "📝 Applying soft delete migration..."
if psql "$DATABASE_URL" -f migrations/add_soft_delete_to_hives.sql 2>&1 | grep -v "^$"; then
    echo "✓ Soft delete migration completed"
fi

echo ""
echo "📝 Applying audio sources timestamps migration..."
if psql "$DATABASE_URL" -f migrations/add_timestamps_to_audio_sources.sql 2>&1 | grep -v "^$"; then
    echo "✓ Audio sources timestamps migration completed"
fi

echo ""
echo "📝 Applying advisory system restructure migration..."
if psql "$DATABASE_URL" -f migrations/restructure_advisory_system.sql 2>&1 | grep -v "^$"; then
    echo "✓ Advisory system restructure migration completed"
fi

echo ""
echo "📝 Seeding advisory action library..."
if psql "$DATABASE_URL" -f migrations/seed_restructured_advisory_data.sql 2>&1 | grep -v "^$"; then
    echo "✓ Advisory action library seeded"
fi

echo ""
echo "📝 Applying circuit breaker migration..."
if psql "$DATABASE_URL" -f migrations/add_circuit_breaker_to_data_sources.sql 2>&1 | grep -v "^$"; then
    echo "✓ Circuit breaker migration completed"
fi

echo ""
echo "✓ All migrations applied successfully"

echo ""
echo "============================================================"
echo "🚀 Starting Uvicorn Server on port ${PORT:-8085}..."
echo "============================================================"
echo ""

exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8085} --log-level info
he