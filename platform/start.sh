#!/bin/bash
# Start backend + frontend
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting backend on :8000..."
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir "$PROJECT/platform/backend" &
BACKEND_PID=$!

echo "Starting frontend on :3000..."
cd "$PROJECT/platform/frontend" && npm run dev -- --port 3000 &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID  Frontend PID: $FRONTEND_PID"
echo "Dashboard → http://localhost:3000"
echo "API        → http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT
wait
