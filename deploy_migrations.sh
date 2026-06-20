#!/bin/bash

# Deployment Migration Script
# Run this on the production server after deploying new code

set -e  # Exit on error

echo "=========================================="
echo "🚀 Running Production Migrations"
echo "=========================================="
echo ""

# Activate virtual environment
echo "1️⃣  Activating virtual environment..."
source venv/bin/activate || source .venv/bin/activate

# Run SQL migrations
echo ""
echo "2️⃣  Running SQL migrations..."
python3 -m api.run_migration

# Migrate admin key from simulation server
echo ""
echo "3️⃣  Migrating admin key..."
python3 -m api.migrate_admin_key || echo "⚠️  Admin key migration skipped (may already exist)"

echo ""
echo "=========================================="
echo "✅ Migrations Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Restart the application"
echo "2. Update admin key with production server URL via API"
echo ""
