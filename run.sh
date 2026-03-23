#!/bin/bash
# Local development launcher for starting SolarShare backend and frontend together.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=3000

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

is_port_in_use() {
  if command_exists lsof; then
    lsof -iTCP:"$1" -sTCP:LISTEN -t >/dev/null 2>&1
    return
  fi

  if command_exists ss; then
    ss -ltn | awk '{print $4}' | grep -qE "[:.]$1$"
    return
  fi

  return 1
}

kill_port_listeners() {
  if ! command_exists lsof; then
    return
  fi

  local pids
  pids="$(lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
  fi
}

echo "Starting SolarShare..."

if ! command_exists npm; then
  echo "npm is not installed or not in PATH."
  echo "Install Node.js, then run setup again."
  exit 1
fi

if [ ! -f "$BACKEND_DIR/venv/bin/activate" ]; then
  echo "Missing backend virtual environment at backend/venv."
  echo "Run one-time setup: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Missing frontend dependencies at frontend/node_modules."
  echo "Run one-time setup: cd frontend && npm install"
  exit 1
fi

if is_port_in_use "$BACKEND_PORT"; then
  echo "Port $BACKEND_PORT is already in use."
  echo "Run ./stop.sh or stop the process using this port, then retry."
  exit 1
fi

if is_port_in_use "$FRONTEND_PORT"; then
  echo "Port $FRONTEND_PORT is already in use."
  echo "Run ./stop.sh or stop the process using this port, then retry."
  exit 1
fi

(
  cd "$BACKEND_DIR"
  source venv/bin/activate
  python main.py
) &
BACKEND_PID=$!

(
  cd "$FRONTEND_DIR"
  npm run dev
) &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  kill_port_listeners "$BACKEND_PORT"
  kill_port_listeners "$FRONTEND_PORT"
}
trap cleanup INT TERM EXIT

echo "Backend running on http://127.0.0.1:8000"
echo "Frontend running on http://localhost:3000"

wait "$BACKEND_PID" "$FRONTEND_PID"
