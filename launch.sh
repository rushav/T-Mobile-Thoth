#!/bin/bash

echo "🔮 Starting Project Thoth..."
echo ""

# Verify required tools are installed before doing anything
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 not found. Install: sudo apt install python3"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "❌ pip3 not found. Install: sudo apt install python3-pip"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ node not found. Install: https://nodejs.org"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm not found. Install: https://nodejs.org"; exit 1; }
# Linux-only: wmctrl is needed to arrange windows in a 2x2 grid
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    command -v wmctrl >/dev/null 2>&1 || { echo "❌ wmctrl not found. Install: sudo apt install wmctrl"; exit 1; }
fi

# Kill any existing processes on our ports
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

# Set up virtual environment (Ubuntu 24 / PEP 668: no system-wide pip installs)
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install dependencies (inside venv, plain `pip` and `python` work)
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt -q

# Seed if first run
if [ ! -f "../data/thoth.db" ]; then
    echo "First run — seeding database..."
    python seed.py
fi

# Start backend
echo "Starting backend on :8000..."
python -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "Waiting for backend..."
for i in {1..30}; do
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        echo "Backend ready!"
        break
    fi
    sleep 1
done

# Start frontend
echo "Starting frontend on :5173..."
cd frontend
npm install -q 2>/dev/null
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to be ready
echo "Waiting for frontend..."
for i in {1..30}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo "Frontend ready!"
        break
    fi
    sleep 1
done

echo ""
echo "========================================="
echo "  Project Thoth is running!"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "========================================="
echo ""

# Detect OS and open 4 browser windows
# Each URL opens a different role view
USER_URL="http://localhost:5173/user"
SME_URL="http://localhost:5173/sme"
ADMIN_URL="http://localhost:5173/admin"
SUPPORT_URL="http://localhost:5173/support"

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS — use AppleScript to arrange windows in 2x2 grid
    echo "Opening 4 windows (macOS)..."

    # Get screen dimensions
    SCREEN_WIDTH=$(osascript -e 'tell application "Finder" to get bounds of window of desktop' 2>/dev/null | cut -d',' -f3 | tr -d ' ' || echo "1920")
    SCREEN_HEIGHT=$(osascript -e 'tell application "Finder" to get bounds of window of desktop' 2>/dev/null | cut -d',' -f4 | tr -d ' ' || echo "1080")

    # Default if detection fails
    SCREEN_WIDTH=${SCREEN_WIDTH:-1920}
    SCREEN_HEIGHT=${SCREEN_HEIGHT:-1080}

    HALF_W=$((SCREEN_WIDTH / 2))
    HALF_H=$((SCREEN_HEIGHT / 2))

    # Open Chrome windows and position them
    # Top-left: User (blue)
    open -na "Google Chrome" --args --new-window --window-size=$HALF_W,$HALF_H --window-position=0,0 "$USER_URL" 2>/dev/null || open "$USER_URL"
    sleep 0.5

    # Top-right: SME (green)
    open -na "Google Chrome" --args --new-window --window-size=$HALF_W,$HALF_H --window-position=$HALF_W,0 "$SME_URL" 2>/dev/null || open "$SME_URL"
    sleep 0.5

    # Bottom-left: Admin (red)
    open -na "Google Chrome" --args --new-window --window-size=$HALF_W,$HALF_H --window-position=0,$HALF_H "$ADMIN_URL" 2>/dev/null || open "$ADMIN_URL"
    sleep 0.5

    # Bottom-right: Support (gray)
    open -na "Google Chrome" --args --new-window --window-size=$HALF_W,$HALF_H --window-position=$HALF_W,$HALF_H "$SUPPORT_URL" 2>/dev/null || open "$SUPPORT_URL"

elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    # Windows (Git Bash / WSL)
    echo "Opening 4 windows (Windows)..."
    start chrome --new-window --window-size=960,540 --window-position=0,0 "$USER_URL" 2>/dev/null
    start chrome --new-window --window-size=960,540 --window-position=960,0 "$SME_URL" 2>/dev/null
    start chrome --new-window --window-size=960,540 --window-position=0,540 "$ADMIN_URL" 2>/dev/null
    start chrome --new-window --window-size=960,540 --window-position=960,540 "$SUPPORT_URL" 2>/dev/null

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux — Chrome's --window-position is ignored on most Linux WMs.
    # Open windows normally, then use wmctrl to arrange them by document.title.
    echo "Opening 4 windows (Linux)..."

    # Detect available browser
    if command -v google-chrome >/dev/null 2>&1; then
        BROWSER="google-chrome"
    elif command -v chromium-browser >/dev/null 2>&1; then
        BROWSER="chromium-browser"
    elif command -v chromium >/dev/null 2>&1; then
        BROWSER="chromium"
    elif command -v firefox >/dev/null 2>&1; then
        BROWSER="firefox"
    else
        echo "❌ No supported browser found. Install Google Chrome."
        exit 1
    fi

    "$BROWSER" --new-window "$USER_URL" &
    sleep 1
    "$BROWSER" --new-window "$SME_URL" &
    sleep 1
    "$BROWSER" --new-window "$ADMIN_URL" &
    sleep 1
    "$BROWSER" --new-window "$SUPPORT_URL" &
    sleep 2

    # Detect screen resolution; fall back to 1920x1080 if xdpyinfo isn't available
    SCREEN=$(xdpyinfo 2>/dev/null | awk '/dimensions:/{print $2}')
    SCREEN_W=$(echo $SCREEN | cut -d'x' -f1)
    SCREEN_H=$(echo $SCREEN | cut -d'x' -f2)
    SCREEN_W=${SCREEN_W:-1920}
    SCREEN_H=${SCREEN_H:-1080}
    HALF_W=$((SCREEN_W / 2))
    HALF_H=$((SCREEN_H / 2))

    # Arrange the 4 windows by their document.title (set in each page's useEffect).
    # wmctrl -e args: gravity,x,y,width,height (gravity 0 = default)
    sleep 1
    wmctrl -r "Thoth — User" -e 0,0,0,$HALF_W,$HALF_H 2>/dev/null
    wmctrl -r "Thoth — SME" -e 0,$HALF_W,0,$HALF_W,$HALF_H 2>/dev/null
    wmctrl -r "Thoth — Admin" -e 0,0,$HALF_H,$HALF_W,$HALF_H 2>/dev/null
    wmctrl -r "Thoth — Support" -e 0,$HALF_W,$HALF_H,$HALF_W,$HALF_H 2>/dev/null
fi

echo ""
echo "4 windows opened in 2x2 grid:"
echo "  Top-left:     USER view (blue)"
echo "  Top-right:    SME view (green)"
echo "  Bottom-left:  ADMIN view (red)"
echo "  Bottom-right: SUPPORT view (gray)"
echo ""
echo "Press Ctrl+C to stop everything."

# Wait and cleanup on exit
trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
