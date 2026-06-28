#!/bin/bash
# Show current public URLs for all environments
echo "=== WINBOT Booking — Public URLs ==="
echo ""

# Dev (ngrok)
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | python3 -c "import json,sys;d=json.load(sys.stdin);[print(t['public_url']) for t in d.get('tunnels',[]) if t.get('public_url')]" 2>/dev/null)
if [ -n "$NGROK_URL" ]; then
    echo "🌐 DEV (ngrok):"
    echo "   $NGROK_URL"
    echo "   $NGROK_URL/admin/login"
    echo ""
fi

# Prod (cloudflared)
if command -v cloudflared &> /dev/null; then
    TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' ~/winbot-booking-app/logs/tunnel.log 2>/dev/null | tail -1)
    if [ -n "$TUNNEL_URL" ]; then
        echo "🚀 PROD (cloudflared):"
        echo "   $TUNNEL_URL"
        echo "   $TUNNEL_URL/admin/login"
        echo ""
    fi
fi

echo "📋 Local:"
echo "   http://localhost:8080"
echo "   http://localhost:8080/admin/login"
