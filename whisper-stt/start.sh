#!/bin/bash
# ============================================================
# Whisper STT Server — Start Script
# ============================================================

cd "$(dirname "$0")"

# Run setup if venv doesn't exist
if [ ! -d "venv" ]; then
    echo "⚙️  First run — running setup..."
    bash setup.sh
fi

source venv/bin/activate

# Model options: tiny (~75MB), base (~145MB), small (~460MB), medium (~1.5GB)
# small = best balance of speed + accuracy for Mac 16GB
export WHISPER_MODEL=${WHISPER_MODEL:-small}
export PORT=${PORT:-9000}

echo "🎙️  Starting Whisper STT Server..."
echo "   Model: $WHISPER_MODEL"
echo "   Port:  $PORT"
echo "   URL:   http://localhost:$PORT"
echo ""
echo "📌 Open WebUI config:"
echo "   Settings → Audio → Speech to Text"
echo "   Engine:   OpenAI API"
echo "   Base URL: http://localhost:$PORT/v1"
echo "   API Key:  local"
echo ""

python server.py
