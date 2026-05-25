#!/bin/bash

# Script to drop and recreate the BSADS database
# Run this script to start with a fresh database

echo "========================================="
echo "BSADS Database Reset"
echo "========================================="
echo ""

# Stop the FastAPI server first!
echo "⚠️  IMPORTANT: Stop your FastAPI server (Ctrl+C) before running this script!"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

echo ""
echo "1. Terminating all connections to bee_db..."
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'bee_db' AND pid <> pg_backend_pid();"

echo ""
echo "2. Dropping database bee_db..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS bee_db;"

echo ""
echo "3. Creating fresh database bee_db..."
sudo -u postgres psql -c "CREATE DATABASE bee_db OWNER bee_user;"

echo ""
echo "4. Running migrations..."

# Run user credentials migration
echo "   - Adding user server credentials columns..."
PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -f migrations/add_user_server_credentials.sql

# Run soft delete migration
echo "   - Adding soft delete columns to hives..."
PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -f migrations/add_soft_delete_to_hives.sql

echo ""
echo "5. Starting FastAPI server to create tables..."
echo "   The server will create all tables automatically on startup."
echo ""
echo "✅ Database reset complete!"
echo ""
echo "Next steps:"
echo "1. Start your FastAPI server: uvicorn api.main:app --reload --port 8001"
echo "2. Register a new user with server_url and api_key"
echo "3. Create hives"
echo "4. Add audio files to: recordings/<api-key>/<hive-id>/"
echo ""
