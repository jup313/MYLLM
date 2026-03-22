#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "⚠️  venv not found. Running setup first..."
    bash setup.sh
fi

source venv/bin/activate

# Kill any existing instance on port 5051
lsof -ti:5051 | xargs kill -9 2>/dev/null; sleep 1

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   📬 Gmail AI Manager                               ║"
echo "║   Open: http://localhost:5051                       ║"
echo "║   Press Ctrl+C to stop                             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Open browser after 2s
(sleep 2 && open http://localhost:5051) &

python3 app.py
