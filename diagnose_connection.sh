#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Diagnose Docker networking issue
# Run this on the production server: bash diagnose_connection.sh
# ══════════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo "🔍 Docker Networking Diagnostics"
echo "═══════════════════════════════════════════════════════════════"
echo ""

CONTAINER_NAME="bsads-api-production"

echo "1️⃣ Checking if container is running..."
if docker ps | grep -q $CONTAINER_NAME; then
    echo "✅ Container is running"
    docker ps | grep $CONTAINER_NAME
else
    echo "❌ Container is not running!"
    exit 1
fi
echo ""

echo "2️⃣ Checking if host.docker.internal is configured in container..."
if docker exec $CONTAINER_NAME cat /etc/hosts | grep -q host.docker.internal; then
    HOST_GATEWAY=$(docker exec $CONTAINER_NAME cat /etc/hosts | grep host.docker.internal | awk '{print $1}')
    echo "✅ host.docker.internal is configured: $HOST_GATEWAY"
else
    echo "❌ host.docker.internal NOT configured!"
    echo "   Container was started without --add-host flag"
    echo ""
    echo "   Fix: Restart container with --add-host=host.docker.internal:host-gateway"
    exit 1
fi
echo ""

echo "3️⃣ Checking if simulation server (port 8086) is running on host..."
if netstat -tuln 2>/dev/null | grep -q ":8086" || ss -tuln 2>/dev/null | grep -q ":8086"; then
    echo "✅ Port 8086 is listening on host"
    netstat -tuln 2>/dev/null | grep ":8086" || ss -tuln 2>/dev/null | grep ":8086"
else
    echo "❌ Port 8086 is NOT listening on host!"
    echo ""
    echo "   The simulation server is not running or not listening on port 8086"
    echo "   Start your simulation server first!"
    echo ""
    echo "   Check with: sudo lsof -i :8086"
    echo "   Or: sudo netstat -tulnp | grep 8086"
fi
echo ""

echo "4️⃣ Testing connection to port 8086 from HOST..."
if curl -s -m 5 http://localhost:8086/health > /dev/null 2>&1; then
    echo "✅ Host can connect to localhost:8086"
    curl -s http://localhost:8086/health | head -c 200
    echo ""
else
    echo "❌ Host CANNOT connect to localhost:8086"
    echo "   Simulation server is not responding"
fi
echo ""

echo "5️⃣ Testing connection from INSIDE container..."
if docker exec $CONTAINER_NAME curl -s -m 5 http://host.docker.internal:8086/health > /dev/null 2>&1; then
    echo "✅ Container CAN connect to host.docker.internal:8086"
    docker exec $CONTAINER_NAME curl -s http://host.docker.internal:8086/health | head -c 200
    echo ""
else
    echo "❌ Container CANNOT connect to host.docker.internal:8086"
    echo ""
    echo "   Checking further..."
    echo ""
    
    # Try to ping the gateway
    echo "   Testing if gateway is reachable..."
    if docker exec $CONTAINER_NAME ping -c 2 $HOST_GATEWAY > /dev/null 2>&1; then
        echo "   ✅ Can ping gateway ($HOST_GATEWAY)"
    else
        echo "   ❌ Cannot ping gateway ($HOST_GATEWAY)"
    fi
    echo ""
    
    # Check if it's a firewall issue
    echo "   This could be:"
    echo "   - Simulation server not running"
    echo "   - Firewall blocking container→host traffic"
    echo "   - Port 8086 only listening on external IP (not localhost)"
fi
echo ""

echo "6️⃣ Checking container's docker run command..."
echo "   Looking for --add-host flag..."
docker inspect $CONTAINER_NAME --format '{{.HostConfig.ExtraHosts}}' | grep -q "host.docker.internal" && \
    echo "✅ Container has --add-host configured" || \
    echo "❌ Container missing --add-host flag!"
echo ""

echo "7️⃣ Checking what's listening on port 8086..."
echo "   Processes listening on port 8086:"
sudo lsof -i :8086 2>/dev/null || echo "   (lsof not available or no process on 8086)"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "📋 Summary & Recommendations"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check all conditions
HAS_HOST_INTERNAL=$(docker exec $CONTAINER_NAME cat /etc/hosts | grep -c host.docker.internal)
PORT_LISTENING=$(netstat -tuln 2>/dev/null | grep -c ":8086" || ss -tuln 2>/dev/null | grep -c ":8086" || echo 0)
HOST_CAN_CONNECT=$(curl -s -m 2 http://localhost:8086/health > /dev/null 2>&1 && echo 1 || echo 0)

if [ "$HAS_HOST_INTERNAL" -eq 0 ]; then
    echo "🔧 FIX NEEDED: Restart container with --add-host flag"
    echo ""
    echo "docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME"
    echo "docker run -d --name $CONTAINER_NAME --add-host=host.docker.internal:host-gateway -p 8085:8085 ..."
    echo ""
elif [ "$PORT_LISTENING" -eq 0 ]; then
    echo "🔧 FIX NEEDED: Start the simulation server on port 8086"
    echo ""
    echo "The simulation server is not running!"
    echo "Start it with the correct command to listen on port 8086"
    echo ""
elif [ "$HOST_CAN_CONNECT" -eq 0 ]; then
    echo "⚠️  Port 8086 is listening but not responding"
    echo ""
    echo "Check if the simulation server is properly configured"
    echo "Try: curl http://localhost:8086/health"
    echo ""
else
    echo "🤔 Configuration looks correct but container cannot connect"
    echo ""
    echo "Possible issues:"
    echo "1. Firewall blocking Docker→Host traffic"
    echo "2. Server only listening on external IP (not 0.0.0.0)"
    echo ""
    echo "Try using host network mode instead:"
    echo "docker run -d --name $CONTAINER_NAME --network host ..."
fi
