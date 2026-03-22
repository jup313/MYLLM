#!/bin/bash
# ============================================================
# Tax AI Social — One-Command Setup
# ============================================================
set -e

echo ""
echo "🚀 Tax AI Social Setup"
echo "======================"
echo ""

cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "❌ Python3 not found. Install from https://python.org"
  exit 1
fi
echo "✅ Python3: $(python3 --version)"

# Create venv
if [ ! -d "venv" ]; then
  echo "📦 Creating Python virtual environment..."
  python3 -m venv venv
fi

# Activate + install
source venv/bin/activate
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q flask requests apscheduler python-dotenv

echo ""
echo "✅ Dependencies installed"
echo ""

# Check Ollama
if command -v ollama &>/dev/null; then
  echo "✅ Ollama found: $(ollama --version 2>/dev/null || echo 'installed')"
  echo "   Run: ollama serve  (in a separate terminal)"
  echo "   Run: ollama pull llama3  (first time only)"
else
  echo "⚠️  Ollama not found. Install with:"
  echo "   brew install ollama"
  echo "   Then: ollama serve && ollama pull llama3"
fi

echo ""
echo "📝 Next steps:"
echo "  1. Edit .env — add your Facebook Page ID and Access Token"
echo "  2. Run: bash start.sh"
echo "  3. Open: http://localhost:5055"
echo ""
echo "✅ Setup complete!"
