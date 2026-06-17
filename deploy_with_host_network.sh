#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Alternative deployment using host network mode
# This is simpler and more reliable on Linux when API and simulation are on same host
# Run this on the production server: bash deploy_with_host_network.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e

DOCKER_IMAGE="bsads2026/bsads-api:latest"
CONTAINER_NAME="bsads-api-production"

echo "═══════════════════════════════════════════════════════════════"
echo "🔧 Deploying with Host Network Mode"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "⚠️  Note: Host network mode means:"
echo "   - Container shares the host's network stack"
echo "   - No port mapping needed (API directly on host port 8085)"
echo "   - Can access localhost:8086 directly (no host.docker.internal)"
echo "   - Less network isolation but simpler connectivity"
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
echo "🚀 Starting container with host network mode..."
docker run -d \
  --name $CONTAINER_NAME \
  --restart unless-stopped \
  --network host \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}" \
  -e HF_SPACE_NAME="${HF_SPACE_NAME:-DerrickLegacy256/bee-audio-classifier}" \
  -e HF_TOKEN="${HF_TOKEN:-your-token-here}" \
  -e PORT=8085 \
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
echo "📊 Recent container logs:"
docker logs --tail 30 $CONTAINER_NAME

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Deployment Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "🌐 API URL:  http://196.43.168.57:8085"
echo "📚 API Docs: http://196.43.168.57:8085/docs"
echo "🏥 Health:   http://196.43.168.57:8085/health"
echo ""
echo "🧪 Test Commands:"
echo ""
echo "1. Test API health:"
echo "   curl http://196.43.168.57:8085/health"
echo ""
echo "2. Test simulation server connection (now uses localhost):"
echo "   docker exec $CONTAINER_NAME curl http://localhost:8086/health"
echo ""
echo "3. Watch live logs:"
echo "   docker logs -f $CONTAINER_NAME"
echo ""
echo "📝 Note: With host network mode, the container can access"
echo "   localhost:8086 directly - no URL translation needed!"
echo ""
