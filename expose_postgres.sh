#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Expose PostgreSQL port for Laravel database access
# Run this on the production server: bash expose_postgres.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e

DOCKER_IMAGE="bsads2026/bsads-api:latest"
CONTAINER_NAME="bsads-api-production"
API_PORT=8085
POSTGRES_PORT=5433  # Using 5433 to avoid conflicts with system PostgreSQL

echo "═══════════════════════════════════════════════════════════════"
echo "🔧 Exposing PostgreSQL for Laravel Access"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "This will restart the container with PostgreSQL exposed on port $POSTGRES_PORT"
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
echo "🚀 Starting container with PostgreSQL exposed..."
docker run -d \
  --name $CONTAINER_NAME \
  --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  -p ${API_PORT}:${API_PORT} \
  -p ${POSTGRES_PORT}:5432 \
  -v bsads-data:/var/lib/postgresql \
  -v bsads-uploads:/app/uploads \
  -e DATABASE_URL="postgresql://bee_user:bee_user@localhost:5432/bee_db" \
  -e SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}" \
  -e HF_SPACE_NAME="${HF_SPACE_NAME:-DerrickLegacy256/bee-audio-classifier}" \
  -e HF_TOKEN="${HF_TOKEN:-your-token-here}" \
  -e PORT=${API_PORT} \
  $DOCKER_IMAGE

echo ""
echo "⏳ Waiting for container to start (20 seconds)..."
sleep 20

echo ""
echo "🔍 Checking container status..."
if docker ps | grep -q $CONTAINER_NAME; then
    echo "✅ Container is running!"
    docker ps | grep $CONTAINER_NAME
else
    echo "❌ Container is not running. Check logs:"
    docker logs $CONTAINER_NAME
    exit 1
fi

echo ""
echo "🔍 Verifying PostgreSQL is accessible..."
sleep 5

if docker exec $CONTAINER_NAME pg_isready -U bee_user -d bee_db > /dev/null 2>&1; then
    echo "✅ PostgreSQL is running and accepting connections"
else
    echo "⚠️  PostgreSQL might still be starting up..."
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ PostgreSQL Exposed Successfully!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📊 Connection Details for Laravel:"
echo "════════════════════════════════════════════════════════════"
echo "DB_CONNECTION=pgsql"
echo "DB_HOST=196.43.168.57"
echo "DB_PORT=${POSTGRES_PORT}"
echo "DB_DATABASE=bee_db"
echo "DB_USERNAME=bee_user"
echo "DB_PASSWORD=bee_user"
echo ""
echo "🌐 API URL:  http://196.43.168.57:${API_PORT}"
echo "🗄️  Database: postgresql://bee_user:bee_user@196.43.168.57:${POSTGRES_PORT}/bee_db"
echo ""
echo "🧪 Test Database Connection:"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "From Laravel server:"
echo "  psql -h 196.43.168.57 -p ${POSTGRES_PORT} -U bee_user -d bee_db"
echo "  (password: bee_user)"
echo ""
echo "From this server:"
echo "  docker exec -it $CONTAINER_NAME psql -U bee_user -d bee_db"
echo ""
echo "⚠️  Firewall Note:"
echo "════════════════════════════════════════════════════════════"
echo "If Laravel is on a different server, you may need to allow"
echo "the firewall to accept connections on port ${POSTGRES_PORT}:"
echo ""
echo "  sudo ufw allow ${POSTGRES_PORT}/tcp"
echo ""
echo "Or allow from specific IP:"
echo "  sudo ufw allow from LARAVEL_IP to any port ${POSTGRES_PORT}"
echo ""
