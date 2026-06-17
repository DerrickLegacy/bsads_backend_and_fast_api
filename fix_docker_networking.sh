#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Quick fix for Docker networking issue - allows container to reach host services
# Run this on the production server: bash fix_docker_networking.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e

DOCKER_IMAGE="bsads2026/bsads-api:latest"
CONTAINER_NAME="bsads-api-production"
SERVER_PORT=8085

echo "═══════════════════════════════════════════════════════════════"
echo "🔧 Fixing Docker Networking + Port Mapping"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "This script will:"
echo "  1. Stop the current container"
echo "  2. Restart with --add-host=host.docker.internal:host-gateway"
echo "  3. Enable port mapping for 8085:8085"
echo ""
echo "This allows the API container to communicate with the simulation"
echo "server at port 8086 on the same host machine."
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "📥 Pulling latest image..."
docker pull $DOCKER_IMAGE

echo ""
echo "🛑 Stopping and removing existing container..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo ""
echo "🚀 Starting new container with networking fix..."
docker run -d \
  --name $CONTAINER_NAME \
  --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  -p ${SERVER_PORT}:${SERVER_PORT} \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}" \
  -e HF_SPACE_NAME="${HF_SPACE_NAME:-DerrickLegacy256/bee-audio-classifier}" \
  -e HF_TOKEN="${HF_TOKEN:-your-token-here}" \
  -e PORT=${SERVER_PORT} \
  $DOCKER_IMAGE

echo ""
echo "⏳ Waiting for container to start (20 seconds)..."
sleep 20

echo ""
echo "🔍 Checking container status..."
if docker ps | grep -q $CONTAINER_NAME; then
    echo "✅ Container is running!"
else
    echo "❌ Container is not running. Check logs:"
    docker logs $CONTAINER_NAME
    exit 1
fi

echo ""
echo "📊 Verifying host.docker.internal is configured..."
if docker exec $CONTAINER_NAME cat /etc/hosts | grep -q host.docker.internal; then
    HOST_INTERNAL_IP=$(docker exec $CONTAINER_NAME cat /etc/hosts | grep host.docker.internal | awk '{print $1}')
    echo "✅ host.docker.internal is configured: $HOST_INTERNAL_IP"
else
    echo "❌ WARNING: host.docker.internal not found in container's /etc/hosts"
    echo "   This might cause connection issues with the simulation server."
fi

echo ""
echo "📋 Recent container logs:"
docker logs --tail 30 $CONTAINER_NAME

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Deployment Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "🌐 API URL:  http://196.43.168.57:${SERVER_PORT}"
echo "📚 API Docs: http://196.43.168.57:${SERVER_PORT}/docs"
echo "🏥 Health:   http://196.43.168.57:${SERVER_PORT}/health"
echo ""
echo "🧪 Test Commands:"
echo ""
echo "1. Test API health:"
echo "   curl http://196.43.168.57:${SERVER_PORT}/health"
echo ""
echo "2. Test simulation server connection from container:"
echo "   docker exec $CONTAINER_NAME curl -v http://host.docker.internal:8086/health"
echo ""
echo "3. Watch live logs:"
echo "   docker logs -f $CONTAINER_NAME"
echo ""
echo "4. Create a test hive (should create folder on simulation server):"
echo "   curl -X POST http://196.43.168.57:${SERVER_PORT}/bsads-api-db/hives \\"
echo "     -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"hive_name\":\"Test Hive\",\"hive_location\":\"Test\",\"hive_type\":\"Box\",\"installation_date\":\"2026-06-17\",\"latitude\":0.39,\"longitude\":0.98,\"owner_id\":\"YOUR_USER_ID\"}'"
echo ""
