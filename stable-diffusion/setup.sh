#!/bin/bash
# setup.sh — Install Stable Diffusion dependencies
# Optimized for Apple Silicon (MPS) and also works on CUDA/CPU

set -e

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   🎨 Stable Diffusion Setup                    ║"
echo "║   Apple Silicon MPS · CUDA · CPU               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Check Python ───────────────────────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install from https://www.python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PYTHON_VERSION found"

# ── Create virtual environment ────────────────────────────────────
VENV_DIR="$(dirname "$0")/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── Install PyTorch (Apple Silicon) ──────────────────────────────
echo ""
echo "🔧 Installing PyTorch..."

OS=$(uname -s)
ARCH=$(uname -m)

if [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
    echo "  🍎 Apple Silicon detected — installing PyTorch with MPS support"
    pip install --upgrade pip wheel
    # PyTorch nightly for best MPS support, or stable
    pip install torch torchvision torchaudio
else
    echo "  💻 Intel/Linux detected"
    pip install torch torchvision torchaudio
fi

# ── Install Diffusers stack ────────────────────────────────────────
echo ""
echo "📦 Installing diffusers, transformers, accelerate..."
pip install -r "$(dirname "$0")/requirements.txt"

# ── Create output directory ───────────────────────────────────────
mkdir -p "$(dirname "$0")/generated"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   ✅ Setup complete!                           ║"
echo "║                                                ║"
echo "║   Run: bash start.sh                          ║"
echo "║   Open: http://localhost:5050                 ║"
echo "║                                               ║"
echo "║   First run downloads the model (~2-7 GB)    ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
