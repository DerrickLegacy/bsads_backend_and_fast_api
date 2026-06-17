#!/bin/bash
# Manual migration script for production server
# Run this once to fix the current production deployment

set -e

SERVER_HOST="196.43.168.57"
SERVER_USER="ademneadev"
CONTAINER_NAME="bsads-api-production"

echo "==================================="
echo "Applying Migration to Production"
echo "==================================="
echo ""
echo "Server: $SERVER_HOST"
echo "Container: $CONTAINER_NAME"
echo ""

# Check if we can reach the server
if ! ssh -o ConnectTimeout=5 "${SERVER_USER}@${SERVER_HOST}" "echo 'Connection OK'" 2>/dev/null; then
    echo "❌ Cannot connect to server. Please ensure:"
    echo "   - You have SSH access to $SERVER_HOST"
    echo "   - You have added your SSH key or password"
    exit 1
fi

echo "✓ SSH connection successful"
echo ""

# Copy migration file to server
echo "📤 Copying migration file to server..."
scp migrations/add_circuit_breaker_to_data_sources.sql "${SERVER_USER}@${SERVER_HOST}:/tmp/"

echo "✓ Migration file copied"
echo ""

# Apply migration inside the Docker container
echo "🔄 Applying migration..."
ssh "${SERVER_USER}@${SERVER_HOST}" << 'ENDSSH'
echo "Running migration inside container..."
docker exec bsads-api-production psql -U bee_user -d bee_db -f /tmp/add_circuit_breaker_to_data_sources.sql

# Copy the migration file into the container for future reference
docker cp /tmp/add_circuit_breaker_to_data_sources.sql bsads-api-production:/app/migrations/

echo "✓ Migration applied successfully"
echo ""
echo "🔄 Restarting container to pick up model changes..."
docker restart bsads-api-production

echo "⏳ Waiting for container to restart..."
sleep 10

echo "✓ Container restarted"
ENDSSH

echo ""
echo "==================================="
echo "✅ Migration Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "  1. Test the API: curl http://$SERVER_HOST:8085/health"
echo "  2. Check logs: ssh $SERVER_USER@$SERVER_HOST 'docker logs $CONTAINER_NAME --tail 50'"
echo "  3. Monitor poller: ssh $SERVER_USER@$SERVER_HOST 'docker logs -f $CONTAINER_NAME | grep poller'"
echo ""
echo "Future deployments will automatically include this migration."
echo ""
