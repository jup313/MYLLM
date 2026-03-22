#!/bin/bash
# ─────────────────────────────────────────────────────────────
# start-ui.sh — Launch TripoSR Web UI
# Opens http://localhost:5050 in your browser
# ─────────────────────────────────────────────────────────────

PIPELINE_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$PIPELINE_DIR/venv"

if [ ! -d "$VENV" ]; then
    echo ""
    echo "❌ Virtual environment not found."
    echo "   Run setup first:  ./setup.sh"
    echo ""
    exit 1
fi

source "$VENV/bin/activate"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   🧊 Starting TripoSR Web UI                        ║"
echo "║   Opening: http://localhost:5050                    ║"
echo "║   Press Ctrl+C to stop                             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Open browser after 2s
(sleep 2 && open "http://localhost:5050") &

python3 "$PIPELINE_DIR/app.py"
