#!/bin/bash
# ============================================================
# Tax AI Social — Start Dashboard
# ============================================================

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "⚠️  venv not found. Running setup first..."
  bash setup.sh
fi

source venv/bin/activate

echo ""
echo "🚀 Starting Tax AI Social Dashboard..."
echo "📊 Open: http://localhost:5055"
echo "Press Ctrl+C to stop"
echo ""

python run.py
