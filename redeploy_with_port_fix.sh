#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Quick redeploy script to fix port mapping issue
# Run this on the production server: bash redeploy_with_port_fix.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e

DOCKER_IMAGE="bsads2026/bsads-api:latest"
CONTAINER_NAME="bsads-api-production"
SERVER_PORT=8085

echo "═══════════════════════════════════════════════════════════════"
echo "🔧 Fixing Port Mapping Issue"
echo "═══════════════════════════════════════════════════════════════"

echo ""
echo "📥 Pulling latest image..."
docker pull $DOCKER_IMAGE

echo ""
echo "🛑 Stopping and removing existing container..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo ""
echo "🚀 Starting new container with correct port mapping..."
docker run -d \
  --name $CONTAINER_NAME \
  --restart unless-stopped \
  -p ${SERVER_PORT}:${SERVER_PORT} \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="${SECRET_KEY:-temporary-key-change-in-production}" \
  -e HF_SPACE_NAME="${HF_SPACE_NAME:-DerrickLegacy256/bee-audio-classifier}" \
  -e HF_TOKEN="${HF_TOKEN:-your-token-here}" \
  -e PORT=${SERVER_PORT} \
  $DOCKER_IMAGE

echo ""
echo "⏳ Waiting for container to start..."
sleep 15

echo ""
echo "🔍 Checking container status..."
docker ps | grep $CONTAINER_NAME

echo ""
echo "📊 Container logs (last 20 lines)..."
docker logs --tail 20 $CONTAINER_NAME

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Redeployment Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "🌐 API URL:  http://196.43.168.57:${SERVER_PORT}"
echo "📚 API Docs: http://196.43.168.57:${SERVER_PORT}/docs"
echo "🏥 Health:   http://196.43.168.57:${SERVER_PORT}/health"
echo ""
echo "💡 Test the API:"
echo "   curl http://196.43.168.57:${SERVER_PORT}/health"
echo ""
