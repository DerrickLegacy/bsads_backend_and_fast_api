#!/bin/bash

echo "🛑 Stopping any existing uvicorn processes..."
pkill -f "uvicorn.*api.main:app" || echo "No existing process found"

sleep 2

echo "🚀 Starting new uvicorn server..."
source venv/bin/activate
python -m uvicorn api.main:app --reload --port 8000

