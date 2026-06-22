#!/bin/bash
# Test script for IoT device integration
# Tests both audio and CSV uploads, then verifies backend processing

set -e

# Configuration
SIMULATION_SERVER="http://localhost:8086"
BACKEND_SERVER="http://localhost:8003/bsads-api-db"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "IoT Device Integration Test"
echo "=========================================="
echo ""

# Check if API key is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: API key not provided${NC}"
    echo "Usage: ./test_device_integration.sh YOUR_FARMER_API_KEY [HIVE_NAME]"
    echo ""
    echo "Example:"
    echo "  ./test_device_integration.sh f47ac10b-58cc-4372-a567-0e02b2c3d479 Hive01"
    exit 1
fi

API_KEY="$1"
HIVE_NAME="${2:-Hive01}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Simulation Server: $SIMULATION_SERVER"
echo "  Backend Server: $BACKEND_SERVER"
echo "  API Key: ${API_KEY:0:8}..."
echo "  Hive Name: $HIVE_NAME"
echo ""

# Step 1: Create test CSV file
echo -e "${YELLOW}Step 1: Creating test CSV file...${NC}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
cat > /tmp/test_conditions.csv << EOF
Date,Temperature,Humidity
$TIMESTAMP,28.5*34.2*25.1,60.3*75.0*45.2
EOF

echo -e "${GREEN}✓ Created test CSV:${NC}"
cat /tmp/test_conditions.csv
echo ""

# Step 2: Upload CSV to simulation server
echo -e "${YELLOW}Step 2: Uploading CSV to simulation server...${NC}"
CSV_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
  "${SIMULATION_SERVER}/conditions/hives/${HIVE_NAME}/upload" \
  -H "x-api-key: ${API_KEY}" \
  -F "file=@/tmp/test_conditions.csv")

HTTP_STATUS=$(echo "$CSV_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$CSV_RESPONSE" | sed '/HTTP_STATUS:/d')

if [ "$HTTP_STATUS" = "201" ]; then
    echo -e "${GREEN}✓ CSV uploaded successfully (201 Created)${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}✗ CSV upload failed (Status: $HTTP_STATUS)${NC}"
    echo "$BODY"
    exit 1
fi
echo ""

# Step 3: Create dummy audio file (if ffmpeg available)
echo -e "${YELLOW}Step 3: Creating test audio file...${NC}"
if command -v ffmpeg &> /dev/null; then
    AUDIO_TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
    AUDIO_FILE="/tmp/10_${AUDIO_TIMESTAMP}.wav"
    ffmpeg -f lavfi -i sine=frequency=1000:duration=2 -ar 44100 "$AUDIO_FILE" -y 2>&1 | grep -E "Output|Duration" || true
    
    if [ -f "$AUDIO_FILE" ]; then
        echo -e "${GREEN}✓ Created test audio file: $AUDIO_FILE${NC}"
        
        # Upload audio
        echo -e "${YELLOW}Step 3b: Uploading audio to simulation server...${NC}"
        AUDIO_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
          "${SIMULATION_SERVER}/recordings/hives/${HIVE_NAME}/upload" \
          -H "x-api-key: ${API_KEY}" \
          -F "file=@${AUDIO_FILE}")
        
        AUDIO_HTTP_STATUS=$(echo "$AUDIO_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
        AUDIO_BODY=$(echo "$AUDIO_RESPONSE" | sed '/HTTP_STATUS:/d')
        
        if [ "$AUDIO_HTTP_STATUS" = "201" ]; then
            echo -e "${GREEN}✓ Audio uploaded successfully (201 Created)${NC}"
            echo "$AUDIO_BODY" | python3 -m json.tool 2>/dev/null || echo "$AUDIO_BODY"
        else
            echo -e "${RED}✗ Audio upload failed (Status: $AUDIO_HTTP_STATUS)${NC}"
            echo "$AUDIO_BODY"
        fi
    fi
else
    echo -e "${YELLOW}⚠ ffmpeg not found, skipping audio upload test${NC}"
fi
echo ""

# Step 4: Wait for backend poller
echo -e "${YELLOW}Step 4: Waiting for backend poller to run (2-3 minutes)...${NC}"
echo "The backend polls the simulation server every 2 minutes."
echo "Waiting 130 seconds for next poll cycle..."
echo ""

for i in {130..1}; do
    printf "\rTime remaining: %3d seconds" $i
    sleep 1
done
echo ""
echo ""

# Step 5: Check database
echo -e "${YELLOW}Step 5: Checking database for new records...${NC}"
echo "Running query: SELECT * FROM hive_conditions ORDER BY created_at DESC LIMIT 5;"
echo ""

DB_RESULT=$(docker exec -it bsads-db psql -U postgres -d bsads -t -c \
  "SELECT condition_id, hive_id, temp_honey, temp_brood, temp_exterior, humidity_honey, humidity_brood, humidity_exterior, recorded_at FROM hive_conditions ORDER BY created_at DESC LIMIT 5;" 2>&1)

if echo "$DB_RESULT" | grep -q "ERROR\|error\|cannot"; then
    echo -e "${RED}✗ Database query failed${NC}"
    echo "$DB_RESULT"
else
    echo -e "${GREEN}✓ Database query successful${NC}"
    echo "$DB_RESULT"
fi
echo ""

# Step 6: Check backend logs
echo -e "${YELLOW}Step 6: Checking backend logs for poller activity...${NC}"
echo "Recent conditions_poller logs:"
echo ""

docker logs bsads-backend 2>&1 | grep "conditions_poller" | tail -10 || echo "No poller logs found yet"
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}Test Complete!${NC}"
echo "=========================================="
echo ""
echo "What to check:"
echo "  1. CSV file was uploaded to simulation server ✓"
echo "  2. Backend poller discovered and processed the file"
echo "  3. Database now contains the new condition records"
echo ""
echo "To manually verify:"
echo "  - Check backend logs: docker logs bsads-backend | grep conditions_poller"
echo "  - Check database: docker exec -it bsads-db psql -U postgres -d bsads -c \"SELECT * FROM hive_conditions;\""
echo "  - List files on simulation server: curl -H 'x-api-key: $API_KEY' $SIMULATION_SERVER/recordings?hive_name=$HIVE_NAME"
echo ""

# Cleanup
rm -f /tmp/test_conditions.csv
rm -f /tmp/10_*.wav
