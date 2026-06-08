#!/bin/bash

# Script to run database migrations on Railway
# Usage: ./run_migration_railway.sh <migration_file.sql>

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if migration file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide a migration file${NC}"
    echo "Usage: ./run_migration_railway.sh migrations/your_migration.sql"
    exit 1
fi

MIGRATION_FILE="$1"

# Check if file exists
if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}Error: Migration file not found: $MIGRATION_FILE${NC}"
    exit 1
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Error: DATABASE_URL environment variable is not set${NC}"
    echo ""
    echo "To get your Railway DATABASE_URL:"
    echo "1. Go to your Railway project dashboard"
    echo "2. Click on the PostgreSQL service"
    echo "3. Go to 'Variables' tab"
    echo "4. Copy the DATABASE_URL value"
    echo ""
    echo "Then run:"
    echo "export DATABASE_URL='postgresql://user:password@host:port/database'"
    echo "./run_migration_railway.sh $MIGRATION_FILE"
    exit 1
fi

echo -e "${YELLOW}Running migration: $MIGRATION_FILE${NC}"
echo -e "${YELLOW}Database: $DATABASE_URL${NC}"
echo ""

# Run the migration
psql "$DATABASE_URL" -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Migration completed successfully!${NC}"
else
    echo ""
    echo -e "${RED}✗ Migration failed!${NC}"
    exit 1
fi
