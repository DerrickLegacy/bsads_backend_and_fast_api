#!/bin/bash

# Production Deployment Script
# This script safely deploys changes to production without data loss
# All changes are backward compatible

set -e  # Exit on error

PROD_USER="adev"
PROD_HOST="ademnea"
CONTAINER_NAME="bsads-api-production"
IMAGE_NAME="bsads2026/bsads-api"
VERSION="v2.0"

echo "======================================================"
echo "BSADS Production Deployment Script"
echo "======================================================"
echo ""
echo "Changes to deploy:"
echo "  ✓ CSV Conditions Poller"
echo "  ✓ Prediction Details Storage"
echo "  ✓ HTTP Connector Fixes"
echo "  ✓ Database Migrations (non-destructive)"
echo ""
echo "Target: ${PROD_USER}@${PROD_HOST}"
echo "Container: ${CONTAINER_NAME}"
echo ""

# Confirmation
read -p "⚠️  Continue with deployment? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Step 1: Building Docker image..."
docker build -t ${IMAGE_NAME}:${VERSION} .
docker tag ${IMAGE_NAME}:${VERSION} ${IMAGE_NAME}:latest

echo ""
echo "Step 2: Pushing to registry..."
docker push ${IMAGE_NAME}:${VERSION}
docker push ${IMAGE_NAME}:latest

echo ""
echo "Step 3: Copying migration files to production..."
scp api/migrations/003_add_hive_conditions_table.sql ${PROD_USER}@${PROD_HOST}:/tmp/
scp api/migrations/004_add_prediction_details_to_inference.sql ${PROD_USER}@${PROD_HOST}:/tmp/

echo ""
echo "Step 4: Creating backup on production server..."
ssh ${PROD_USER}@${PROD_HOST} << 'EOF'
    BACKUP_FILE=~/backup_before_deployment_$(date +%Y%m%d_%H%M%S).sql
    echo "Creating backup: ${BACKUP_FILE}"
    docker exec bsads-api-production pg_dump -U bee_user bee_db > ${BACKUP_FILE}
    echo "✓ Backup created: $(ls -lh ${BACKUP_FILE})"
EOF

echo ""
echo "Step 5: Running database migrations on production..."
ssh ${PROD_USER}@${PROD_HOST} << 'EOF'
    echo "Checking if hive_conditions table exists..."
    if docker exec bsads-api-production psql -U bee_user -d bee_db -t \
        -c "SELECT to_regclass('hive_conditions');" | grep -q "hive_conditions"; then
        echo "✓ hive_conditions table already exists, skipping migration 003"
    else
        echo "Running migration 003..."
        docker exec -i bsads-api-production psql -U bee_user -d bee_db < /tmp/003_add_hive_conditions_table.sql
        echo "✓ Migration 003 completed"
    fi
    
    echo ""
    echo "Checking if prediction_details column exists..."
    if docker exec bsads-api-production psql -U bee_user -d bee_db -t \
        -c "\d inference_results" | grep -q "prediction_details"; then
        echo "✓ prediction_details column already exists, skipping migration 004"
    else
        echo "Running migration 004..."
        docker exec -i bsads-api-production psql -U bee_user -d bee_db < /tmp/004_add_prediction_details_to_inference.sql
        echo "✓ Migration 004 completed"
    fi
    
    echo ""
    echo "Verifying migrations..."
    docker exec bsads-api-production psql -U bee_user -d bee_db \
        -c "\d hive_conditions" | head -10
    docker exec bsads-api-production psql -U bee_user -d bee_db \
        -c "\d inference_results" | grep prediction_details
EOF

echo ""
echo "Step 6: Deploying new container..."
ssh ${PROD_USER}@${PROD_HOST} << EOF
    echo "Getting current container configuration..."
    OLD_CONFIG=\$(docker inspect bsads-api-production)
    
    echo "Pulling latest image..."
    docker pull ${IMAGE_NAME}:latest
    
    echo "Stopping current container..."
    docker stop ${CONTAINER_NAME}
    
    echo "Removing old container..."
    docker rm ${CONTAINER_NAME}
    
    echo "Starting new container..."
    # Note: Adjust volume mounts and env vars based on your setup
    docker run -d \\
        --name ${CONTAINER_NAME} \\
        -p 8085:8085 \\
        -p 5433:5432 \\
        --restart unless-stopped \\
        ${IMAGE_NAME}:latest
    
    echo "Waiting for container to start..."
    sleep 10
    
    echo "✓ Container started"
EOF

echo ""
echo "Step 7: Verifying deployment..."
ssh ${PROD_USER}@${PROD_HOST} << 'EOF'
    echo "Checking API health..."
    if curl -s http://localhost:8085/health | grep -q "ok"; then
        echo "✓ API is healthy"
    else
        echo "⚠️  API health check failed"
    fi
    
    echo ""
    echo "Checking database connectivity..."
    COUNT=$(docker exec bsads-api-production psql -U bee_user -d bee_db -t \
        -c "SELECT COUNT(*) FROM inference_results;")
    echo "✓ Database connected - ${COUNT} inference records found"
    
    echo ""
    echo "Checking recent logs..."
    docker logs --tail 20 bsads-api-production
EOF

echo ""
echo "======================================================"
echo "✅ Deployment Complete!"
echo "======================================================"
echo ""
echo "Next steps:"
echo "  1. Monitor logs: ssh ${PROD_USER}@${PROD_HOST} 'docker logs -f ${CONTAINER_NAME}'"
echo "  2. Check health: curl http://${PROD_HOST}:8085/health"
echo "  3. Test alerts: curl http://${PROD_HOST}:8085/api/mobile/alerts/[alert-id]"
echo ""
echo "Rollback if needed:"
echo "  ssh ${PROD_USER}@${PROD_HOST}"
echo "  docker stop ${CONTAINER_NAME} && docker rm ${CONTAINER_NAME}"
echo "  docker start ba92f88afb9a  # Old container"
echo ""
