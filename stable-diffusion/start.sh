#!/bin/bash
# start.sh — Start Stable Diffusion image generation server

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   🎨 Stable Diffusion — Starting...            ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Activate virtualenv if it exists
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    echo "✅ Virtual environment activated"
else
    echo "⚠️  No venv found — run 'bash setup.sh' first"
    echo "   Attempting to run with system Python..."
fi

# Allow env overrides
export SD_MODEL="${SD_MODEL:-sdxl-turbo}"
export SD_PORT="${SD_PORT:-5050}"

echo "🧠 Model:  $SD_MODEL"
echo "🌐 Port:   $SD_PORT"
echo "📁 Images: $SCRIPT_DIR/generated/"
echo ""
echo "→ Opening http://localhost:$SD_PORT"
echo ""

# macOS: open browser after 3s
if command -v open &>/dev/null; then
    (sleep 3 && open "http://localhost:$SD_PORT") &
fi

cd "$SCRIPT_DIR"
python3 app.py
