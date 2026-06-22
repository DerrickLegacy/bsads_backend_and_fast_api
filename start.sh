#!/bin/sh
set -e

echo "============================================================"
echo "🐝 BSADS API - Container Starting"
echo "============================================================"

echo ""
echo "📊 Environment Check:"
echo "  PORT: ${PORT:-8000}"
echo "  DATABASE: $(echo $database_url | sed 's/:\/\/.*@/:\/\/***@/')"  # Hide password in logs
echo ""

echo "🔄 Running database migrations..."

# Railway uses lowercase database_url, handle both cases
DB_URL="${database_url:-${DATABASE_URL:-$POSTGRES_URL}}"

if [ -n "$DB_URL" ]; then
    echo "✓ Database URL found"
    
    echo ""
    echo "📝 Applying user credentials migration..."
    if psql "$DB_URL" -f migrations/add_user_server_credentials.sql 2>&1 | grep -v "^$"; then
        echo "✓ User credentials migration completed"
    fi
    
    echo ""
    echo "📝 Applying soft delete migration..."
    if psql "$DB_URL" -f migrations/add_soft_delete_to_hives.sql 2>&1 | grep -v "^$"; then
        echo "✓ Soft delete migration completed"
    fi
    
    echo ""
    echo "📝 Applying audio sources timestamps migration..."
    if psql "$DB_URL" -f migrations/add_timestamps_to_audio_sources.sql 2>&1 | grep -v "^$"; then
        echo "✓ Audio sources timestamps migration completed"
    fi
    
    echo ""
    echo "📝 Applying advisory system restructure migration..."
    if psql "$DB_URL" -f migrations/restructure_advisory_system.sql 2>&1 | grep -v "^$"; then
        echo "✓ Advisory system restructure migration completed"
    fi
    
    echo ""
    echo "📝 Seeding advisory action library..."
    if psql "$DB_URL" -f migrations/seed_restructured_advisory_data.sql 2>&1 | grep -v "^$"; then
        echo "✓ Advisory action library seeded"
    fi

    echo ""
    echo "📝 Applying admin keys migration..."
    if psql "$DB_URL" -f api/migrations/001_add_admin_keys_table.sql 2>&1 | grep -v "^$"; then
        echo "✓ Admin keys migration completed"
    fi

    echo ""
    echo "📝 Applying nullable user credentials migration..."
    if psql "$DB_URL" -f api/migrations/002_make_user_credentials_nullable.sql 2>&1 | grep -v "^$"; then
        echo "✓ Nullable user credentials migration completed"
    fi

    echo ""
    echo "📝 Applying hive conditions table migration..."
    if psql "$DB_URL" -f api/migrations/003_add_hive_conditions_table.sql 2>&1 | grep -v "^$"; then
        echo "✓ Hive conditions table migration completed"
    fi

    echo ""
    echo "📝 Applying prediction details migration..."
    if psql "$DB_URL" -f api/migrations/004_add_prediction_details_to_inference.sql 2>&1 | grep -v "^$"; then
        echo "✓ Prediction details migration completed"
    fi
    
    echo ""
    echo "✓ All migrations applied successfully"
else
    echo "⚠️  WARNING: No database URL found!"
    echo "   Checked: database_url, DATABASE_URL, POSTGRES_URL"
fi

echo ""
echo "============================================================"
echo "🚀 Starting Uvicorn Server..."
echo "============================================================"
echo ""

exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --log-level info
