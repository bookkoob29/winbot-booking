#!/bin/bash
# ============================================
# WINBOT Booking — Development Environment
# Usage: ./scripts/dev.sh
# 
# Starts:
#   1. FastAPI server (port 8080) with auto-reload
#   2. ngrok tunnel (public URL for testing)
# 
# ALWAYS test changes here FIRST before prod!
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "  WINBOT Booking — DEV Environment"
echo "=========================================="
echo ""

# Clean up any old processes
echo "[1/3] Cleaning up old processes..."
pkill -f "uvicorn app:app" 2>/dev/null || true
pkill -f "ngrok http 8080" 2>/dev/null || true
sleep 1

# Reset DB for clean testing
echo "[2/3] Starting fresh database..."
rm -f "$PROJECT_DIR/bookings.db"

# Start FastAPI server (with auto-reload for dev)
echo "[3/3] Starting services..."
echo ""
cd "$PROJECT_DIR"
python3 -m uvicorn app:app --host 0.0.0.0 --port 8080 --reload &
FASTAPI_PID=$!

# Wait for server to be ready
sleep 3
if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
    echo "  ✅ FastAPI running on http://localhost:8080"
else
    echo "  ❌ FastAPI failed to start"
    exit 1
fi

# Start ngrok tunnel
ngrok http 8080 --log=stdout > /dev/null 2>&1 &
NGROK_PID=$!
sleep 3

# Get ngrok URL
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | python3 -c "import json,sys;d=json.load(sys.stdin);[print(t['public_url']) for t in d.get('tunnels',[]) if t.get('public_url')]" 2>/dev/null)

echo ""
echo "=========================================="
echo "  🌐 DEV Environment Ready!"
echo "=========================================="
echo ""
echo "  Local:    http://localhost:8080"
echo "  Public:   $NGROK_URL"
echo "  Admin:    $NGROK_URL/admin/login"
echo "  Passcode: BooK2905@1990"
echo ""
echo "  To stop:  kill $FASTAPI_PID $NGROK_PID"
echo "            or:  pkill -f 'uvicorn app:app'"
echo "=========================================="

# Wait for both processes
wait
