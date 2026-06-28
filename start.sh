#!/bin/bash
# Render start script — runs uvicorn with PORT from environment
cd "$(dirname "$0")"
exec python3 -m uvicorn app:app --host 0.0.0.0 --port "${PORT:-10000}"
