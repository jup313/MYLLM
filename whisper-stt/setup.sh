#!/bin/bash
# ============================================================
# Whisper STT Server — Setup Script
# Local speech-to-text for Open WebUI (100% private)
# ============================================================

set -e

echo "🎙️  Setting up Local Whisper STT Server..."
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 is required. Install it from https://python.org"
    exit 1
fi

PYTHON=$(command -v python3)
echo "✅ Python: $($PYTHON --version)"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON -m venv venv
fi

source venv/bin/activate

echo "📦 Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Start the server:"
echo "   bash start.sh"
echo ""
echo "📌 Then configure Open WebUI:"
echo "   Settings → Audio → Speech to Text"
echo "   Engine: OpenAI"
echo "   Base URL: http://localhost:9000/v1"
echo "   API Key: local"
echo ""
echo "🎤 First startup will download the Whisper 'small' model (~460MB)"
