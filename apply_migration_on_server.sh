#!/bin/bash
# Run this script DIRECTLY ON THE PRODUCTION SERVER (after SSH)
# Usage: ssh ademneadev@196.43.168.57
#        bash apply_migration_on_server.sh

set -e

CONTAINER_NAME="bsads-api-production"

echo "==================================="
echo "Applying Migration to Production"
echo "==================================="
echo "Container: $CONTAINER_NAME"
echo ""

# Check if migration file exists in /tmp
if [ ! -f /tmp/add_circuit_breaker_to_data_sources.sql ]; then
    echo "❌ Migration file not found at /tmp/add_circuit_breaker_to_data_sources.sql"
    echo ""
    echo "Please copy it first:"
    echo "  scp migrations/add_circuit_breaker_to_data_sources.sql ademneadev@196.43.168.57:/tmp/"
    echo ""
    exit 1
fi

echo "✓ Migration file found"
echo ""

# Check if container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ Container $CONTAINER_NAME is not running"
    docker ps -a | grep "$CONTAINER_NAME" || echo "Container not found at all!"
    exit 1
fi

echo "✓ Container is running"
echo ""

# Apply migration
echo "🔄 Applying migration..."
docker exec "$CONTAINER_NAME" psql -U bee_user -d bee_db -f /tmp/add_circuit_breaker_to_data_sources.sql

echo "✓ Migration applied successfully"
echo ""

# Copy migration into container for future reference
echo "📁 Copying migration into container..."
docker cp /tmp/add_circuit_breaker_to_data_sources.sql "$CONTAINER_NAME:/app/migrations/"

echo "✓ Migration file copied to container"
echo ""

# Verify the column was added
echo "🔍 Verifying migration..."
docker exec "$CONTAINER_NAME" psql -U bee_user -d bee_db -c "\d farmer_data_sources" | grep last_error_at

echo "✓ Column verified"
echo ""

# Restart container
echo "🔄 Restarting container..."
docker restart "$CONTAINER_NAME"

echo "⏳ Waiting for container to restart..."
sleep 10

# Check if container is running
if docker ps | grep -q "$CONTAINER_NAME"; then
    echo "✓ Container restarted successfully"
else
    echo "❌ Container failed to restart"
    echo "Check logs: docker logs $CONTAINER_NAME --tail 50"
    exit 1
fi

echo ""
echo "==================================="
echo "✅ Migration Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "  1. Check logs: docker logs $CONTAINER_NAME --tail 50"
echo "  2. Monitor poller: docker logs -f $CONTAINER_NAME | grep poller"
echo "  3. Test health: curl http://localhost:8085/health"
echo ""
