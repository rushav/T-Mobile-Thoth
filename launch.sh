#!/bin/bash
# launch.sh — start backend + frontend, open one browser tab.
#
# First-run setup creates a venv, installs deps, and seeds the database.
# Subsequent runs skip those steps.

set -euo pipefail

echo "Starting Project Thoth..."

# Verify required tools
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 not found"; exit 1; }
command -v node    >/dev/null 2>&1 || { echo "❌ node not found"; exit 1; }
command -v npm     >/dev/null 2>&1 || { echo "❌ npm not found"; exit 1; }

# Free our ports if anything is squatting
lsof -ti:8000 | xargs -r kill -9 2>/dev/null || true
lsof -ti:5173 | xargs -r kill -9 2>/dev/null || true

# venv (Ubuntu 24+ / PEP 668 requires this — no system-wide pip installs)
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# Backend deps + seed on first run
echo "Installing backend dependencies..."
pushd backend >/dev/null
pip install -r requirements.txt -q
if [ ! -f "../data/thoth.db" ]; then
    echo "First run — seeding database..."
    python seed.py
fi

echo "Starting backend on :8000..."
python -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
popd >/dev/null

# Wait for backend
echo "Waiting for backend..."
for _ in $(seq 1 30); do
    if curl -sf http://localhost:8000/docs >/dev/null 2>&1; then echo "Backend ready."; break; fi
    sleep 1
done

# Frontend
pushd frontend >/dev/null
echo "Installing frontend dependencies..."
npm install -q 2>/dev/null
echo "Starting frontend on :5173..."
npm run dev &
FRONTEND_PID=$!
popd >/dev/null

# Wait for frontend
echo "Waiting for frontend..."
for _ in $(seq 1 30); do
    if curl -sf http://localhost:5173 >/dev/null 2>&1; then echo "Frontend ready."; break; fi
    sleep 1
done

echo ""
echo "========================================="
echo "  Project Thoth is running!"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "========================================="
echo ""

# Open one browser tab
URL="http://localhost:5173"
case "${OSTYPE:-}" in
    darwin*)  open "$URL" 2>/dev/null || true ;;
    msys*|cygwin*|win32) start "$URL" 2>/dev/null || true ;;
    *)        xdg-open "$URL" >/dev/null 2>&1 || true ;;
esac

# Hand control back to the user; ctrl-c here kills the children too.
trap 'kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null; exit 0' INT TERM
wait "$BACKEND_PID" "$FRONTEND_PID"
