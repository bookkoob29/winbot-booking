#!/bin/bash
# ============================================
# WINBOT Booking — Production Environment Setup
# Usage: ./scripts/setup-prod.sh
#
# Installs and configures:
#   1. launchd service — auto-starts FastAPI on boot
#   2. cloudflared tunnel — permanent public URL
#   3. Auto-restart on crash (launchd handles this)
#
# Prerequisites: Homebrew (for cloudflared)
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_DIR="$HOME/Library/LaunchAgents"

echo "=========================================="
echo "  WINBOT Booking — PROD Setup"
echo "=========================================="
echo ""

# 1. Install cloudflared if needed
echo "[1/4] Checking cloudflared..."
if ! command -v cloudflared &> /dev/null; then
    echo "  Installing cloudflared via Homebrew..."
    brew install cloudflared
else
    echo "  ✅ cloudflared already installed"
fi

# 2. Create production start script
echo "[2/4] Creating production start script..."
cat > "$PROJECT_DIR/scripts/start-prod.sh" << 'EOF'
#!/bin/bash
# WINBOT Booking — Production Start
# Run by launchd on boot. Do not run manually.
cd "$(dirname "$0")/.."
export HOST="0.0.0.0"
export PORT=8081
exec python3 -m uvicorn app:app --host 0.0.0.0 --port 8081
EOF
chmod +x "$PROJECT_DIR/scripts/start-prod.sh"
echo "  ✅ Created scripts/start-prod.sh"

# 3. Create launchd plist for FastAPI
echo "[3/4] Creating launchd service (auto-start on boot)..."
mkdir -p "$PLIST_DIR"

cat > "$PLIST_DIR/com.winbot.booking.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.winbot.booking</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/scripts/start-prod.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOST</key>
        <string>0.0.0.0</string>
        <key>PORT</key>
        <string>8080</string>
    </dict>
</dict>
</plist>
PLIST

mkdir -p "$PROJECT_DIR/logs"
echo "  ✅ Created $PLIST_DIR/com.winbot.booking.plist"

# 4. Create cloudflared tunnel service
echo "[4/4] Creating cloudflared tunnel service..."

cat > "$PLIST_DIR/com.winbot.booking-tunnel.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.winbot.booking-tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/cloudflared</string>
        <string>tunnel</string>
        <string>--url</string>
        <string>http://localhost:8081</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/tunnel.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/tunnel.log</string>
</dict>
</plist>
PLIST
echo "  ✅ Created $PLIST_DIR/com.winbot.booking-tunnel.plist"

echo ""
echo "=========================================="
echo "  ✅ PROD Setup Complete!"
echo "=========================================="
echo ""
echo "  To START both services now:"
echo "    launchctl load $PLIST_DIR/com.winbot.booking.plist"
echo "    launchctl load $PLIST_DIR/com.winbot.booking-tunnel.plist"
echo ""
echo "  To STOP:"
echo "    launchctl unload $PLIST_DIR/com.winbot.booking.plist"
echo "    launchctl unload $PLIST_DIR/com.winbot.booking-tunnel.plist"
echo ""
echo "  To check status:"
echo "    launchctl list | grep winbot"
echo ""
echo "  Logs:"
echo "    tail -f $PROJECT_DIR/logs/stdout.log"
echo "    tail -f $PROJECT_DIR/logs/tunnel.log"
echo ""
echo "  ⚠️  After loading, get the tunnel URL:"
echo "     Check $PROJECT_DIR/logs/tunnel.log for"
echo "     'https://xxxx.trycloudflare.com'"
echo ""
echo "=========================================="
