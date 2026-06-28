#!/bin/bash
# WINBOT Booking — Production Start
# Run by launchd on boot. Do not run manually.
cd "$(dirname "$0")/.."
export HOST="0.0.0.0"
export PORT=8081
exec /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m uvicorn app:app --host 0.0.0.0 --port 8081
