#!/bin/bash
# Stops local SolarShare backend and frontend development processes.

pkill -f "python main.py" || true
pkill -f "uvicorn app.main:app" || true
pkill -f "next dev" || true
pkill -f "npm run dev" || true
pkill -f "/bin/bash ./run.sh" || true

if command -v lsof >/dev/null 2>&1; then
  BACKEND_PIDS="$(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null || true)"
  FRONTEND_PIDS="$(lsof -tiTCP:3000 -sTCP:LISTEN 2>/dev/null || true)"
  [ -n "$BACKEND_PIDS" ] && kill $BACKEND_PIDS 2>/dev/null || true
  [ -n "$FRONTEND_PIDS" ] && kill $FRONTEND_PIDS 2>/dev/null || true
fi

echo "Stopped SolarShare"
