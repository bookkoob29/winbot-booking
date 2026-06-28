#!/bin/bash
# WINBOT Mini 2 Booking Website — Run Script
# Usage: ./run.sh [port]

PORT=${1:-8080}
export HOST="0.0.0.0"
export PORT=$PORT

echo "🚀 Starting WINBOT Booking App on http://0.0.0.0:$PORT"
echo "📅 Open http://localhost:$PORT in your browser"
echo "🔐 Admin: http://localhost:$PORT/admin/login"
echo ""

cd "$(dirname "$0")"
python3 -m uvicorn app:app --host 0.0.0.0 --port $PORT --reload
