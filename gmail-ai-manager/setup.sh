#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   📬 Gmail AI Manager — Setup                       ║"
echo "║   Local LLM-powered Gmail on Mac 16GB               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Python check ─────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 not found. Install via: brew install python@3.11"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PYTHON_VERSION found"

# ── Virtual environment ───────────────────────────────────────────
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "✅ Virtual environment active"

# ── Install dependencies ──────────────────────────────────────────
echo ""
echo "📦 Installing Python dependencies..."
pip install --upgrade pip --quiet

pip install \
    flask \
    flask-cors \
    google-auth \
    google-auth-oauthlib \
    google-auth-httplib2 \
    google-api-python-client \
    requests \
    --quiet

echo "✅ Dependencies installed"

# ── Ollama check ──────────────────────────────────────────────────
echo ""
if command -v ollama &>/dev/null; then
    echo "✅ Ollama found: $(ollama --version 2>/dev/null | head -1)"
    echo "   Available models:"
    ollama list 2>/dev/null | tail -n +2 | head -5 | while read line; do echo "   - $line"; done
else
    echo "⚠️  Ollama not found."
    echo "   Install: brew install ollama"
    echo "   Then:    ollama pull mistral:7b"
    echo "   Then:    ollama serve"
fi

# ── Init database ─────────────────────────────────────────────────
echo ""
echo "🗄️  Initializing database..."
python3 -c "from database import init_db; init_db()" 2>/dev/null && echo "✅ Database ready" || echo "⚠️  DB init warning (will retry on first run)"

# ── Done ─────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✅ Setup complete!                                ║"
echo "║                                                      ║"
echo "║   Next steps:                                        ║"
echo "║   1. Run:  ./start.sh                               ║"
echo "║   2. Open: http://localhost:5051                    ║"
echo "║   3. Complete the Setup Wizard (Google API + LLM)  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
