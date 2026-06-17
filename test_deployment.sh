#!/bin/bash

# ══════════════════════════════════════════════════════════════════════════════
# DEPLOYMENT VERIFICATION SCRIPT
# ══════════════════════════════════════════════════════════════════════════════
# Run this to verify your deployment is working correctly
# Can be run locally or as part of CI/CD pipeline
#
# Usage:
#   ./test_deployment.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e

SERVER_HOST="196.43.168.57"
SERVER_PORT="8080"
BASE_URL="http://$SERVER_HOST:$SERVER_PORT"

echo "════════════════════════════════════════════════════════════════════════════"
echo "🧪 BSADS API - Deployment Testing"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Testing deployment at: $BASE_URL"
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local name=$1
    local endpoint=$2
    local expected_status=${3:-200}
    
    echo -n "Testing $name... "
    
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>/dev/null)
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$status_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $status_code)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $status_code, expected $expected_status)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test 1: Health Check
echo "─────────────────────────────────────────────────────────────────────────────"
echo "Test 1: Health Check Endpoint"
echo "─────────────────────────────────────────────────────────────────────────────"
test_endpoint "Health endpoint" "/health" 200
echo ""

# Test 2: Root Endpoint
echo "─────────────────────────────────────────────────────────────────────────────"
echo "Test 2: Root Endpoint"
echo "─────────────────────────────────────────────────────────────────────────────"
test_endpoint "Root endpoint" "/" 200
echo ""

# Test 3: OpenAPI Schema
echo "─────────────────────────────────────────────────────────────────────────────"
echo "Test 3: OpenAPI Schema"
echo "─────────────────────────────────────────────────────────────────────────────"
test_endpoint "OpenAPI schema" "/openapi.json" 200
echo ""

# Test 4: API Documentation
echo "─────────────────────────────────────────────────────────────────────────────"
echo "Test 4: API Documentation"
echo "─────────────────────────────────────────────────────────────────────────────"
test_endpoint "Swagger docs" "/docs" 200
test_endpoint "ReDoc" "/redoc" 200
echo ""

# Test 5: Container Status (SSH Required)
echo "─────────────────────────────────────────────────────────────────────────────"
echo "Test 5: Container Status"
echo "─────────────────────────────────────────────────────────────────────────────"
echo -n "Checking container status... "
if ssh ademneadev@$SERVER_HOST 'docker ps | grep bsads-api-production' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} (Container is running)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} (Container not found or not running)"
    ((TESTS_FAILED++))
fi
echo ""

# Test 6: Database Connection (SSH Required)
echo "─────────────────────────────────────────────────────────────────────────────"
echo "Test 6: Database Connection"
echo "─────────────────────────────────────────────────────────────────────────────"
echo -n "Testing database connection... "
if ssh ademneadev@$SERVER_HOST 'docker exec bsads-api-production psql -U bee_user -d bee_db -c "SELECT 1" > /dev/null 2>&1'; then
    echo -e "${GREEN}✓ PASS${NC} (Database is accessible)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} (Cannot connect to database)"
    ((TESTS_FAILED++))
fi
echo ""

# Test 7: FastAPI Process (SSH Required)
echo "─────────────────────────────────────────────────────────────────────────────"
echo "Test 7: FastAPI Process"
echo "─────────────────────────────────────────────────────────────────────────────"
echo -n "Checking FastAPI process... "
if ssh ademneadev@$SERVER_HOST 'docker exec bsads-api-production ps aux | grep uvicorn | grep -v grep' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} (FastAPI is running)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} (FastAPI process not found)"
    ((TESTS_FAILED++))
fi
echo ""

# Test 8: PostgreSQL Process (SSH Required)
echo "─────────────────────────────────────────────────────────────────────────────"
echo "Test 8: PostgreSQL Process"
echo "─────────────────────────────────────────────────────────────────────────────"
echo -n "Checking PostgreSQL process... "
if ssh ademneadev@$SERVER_HOST 'docker exec bsads-api-production ps aux | grep postgres | grep -v grep' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} (PostgreSQL is running)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} (PostgreSQL process not found)"
    ((TESTS_FAILED++))
fi
echo ""

# Test 9: Docker Volumes (SSH Required)
echo "─────────────────────────────────────────────────────────────────────────────"
echo "Test 9: Data Persistence (Docker Volumes)"
echo "─────────────────────────────────────────────────────────────────────────────"
echo -n "Checking data volumes... "
volume_count=$(ssh ademneadev@$SERVER_HOST 'docker volume ls | grep bsads' | wc -l)
if [ "$volume_count" -ge 2 ]; then
    echo -e "${GREEN}✓ PASS${NC} (Found $volume_count volumes)"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ WARNING${NC} (Expected 2 volumes, found $volume_count)"
    ((TESTS_FAILED++))
fi
echo ""

# Summary
echo "════════════════════════════════════════════════════════════════════════════"
echo "📊 Test Summary"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! Deployment is successful.${NC}"
    echo ""
    echo "🌐 Your API is live at:"
    echo "   - API: $BASE_URL"
    echo "   - Docs: $BASE_URL/docs"
    echo "   - Redoc: $BASE_URL/redoc"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review the output above.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  - View logs: ssh ademneadev@$SERVER_HOST 'docker logs bsads-api-production'"
    echo "  - Check status: ssh ademneadev@$SERVER_HOST 'docker ps'"
    echo "  - Restart: ssh ademneadev@$SERVER_HOST 'docker restart bsads-api-production'"
    echo ""
    exit 1
fi
