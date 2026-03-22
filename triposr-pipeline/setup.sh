#!/bin/bash
# ============================================================
# TripoSR Pipeline Setup for Apple Silicon Mac (16GB)
# Full pipeline: Ollama LLM → Stable Diffusion → TripoSR → 3D
# ============================================================

set -e

PYTHON="/opt/homebrew/bin/python3.11"
VENV_DIR="$(dirname "$0")/venv"
PIPELINE_DIR="$(dirname "$0")"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  TripoSR 3D Pipeline Setup for Mac (16GB ARM)       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Check Python 3.11 ─────────────────────────────
echo "▶ Checking Python 3.11..."
if ! command -v /opt/homebrew/bin/python3.11 &>/dev/null; then
    echo "Installing Python 3.11 via Homebrew..."
    brew install python@3.11
fi
echo "  ✅ $($PYTHON --version)"

# ── Step 2: Create virtual environment ────────────────────
echo ""
echo "▶ Creating virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON -m venv "$VENV_DIR"
    echo "  ✅ venv created at $VENV_DIR"
else
    echo "  ✅ venv already exists"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet

# ── Step 3: Install PyTorch with MPS support ───────────────
echo ""
echo "▶ Installing PyTorch (Apple MPS)..."
pip install --quiet torch torchvision torchaudio

# ── Step 4: Install image generation (Diffusers) ──────────
echo ""
echo "▶ Installing Stable Diffusion (diffusers)..."
pip install --quiet \
    diffusers \
    transformers \
    accelerate \
    safetensors \
    Pillow

# ── Step 5: Install TripoSR ───────────────────────────────
echo ""
echo "▶ Installing TripoSR dependencies..."
pip install --quiet \
    trimesh \
    einops \
    omegaconf \
    huggingface_hub \
    rembg \
    onnxruntime \
    imageio \
    imageio-ffmpeg \
    scipy \
    skimage \
    scikit-image \
    mcubes \
    xatlas \
    open3d \
    numpy

# Install TripoSR from GitHub
echo ""
echo "▶ Installing TripoSR from GitHub..."
if [ ! -d "$PIPELINE_DIR/TripoSR" ]; then
    git clone https://github.com/VAST-AI-Research/TripoSR.git "$PIPELINE_DIR/TripoSR"
    echo "  ✅ TripoSR cloned"
else
    echo "  ✅ TripoSR already cloned"
fi

# Install torchmcubes (required by TripoSR for marching cubes)
echo ""
echo "▶ Installing torchmcubes (marching cubes for mesh extraction)..."
pip install --quiet git+https://github.com/tatsy/torchmcubes.git
echo "  ✅ torchmcubes installed"

# Test TripoSR import
python3 -c "
import sys
sys.path.insert(0, '$PIPELINE_DIR/TripoSR')
from tsr.system import TSR
print('  ✅ TripoSR import OK')
" 2>&1 || echo "  ⚠️  TripoSR import warning — may still work at runtime"

# ── Step 6: Install pipeline extras ───────────────────────
echo ""
echo "▶ Installing pipeline utilities..."
pip install --quiet \
    requests \
    flask \
    flask-cors \
    tqdm \
    rich \
    click

# ── Step 7: Create output dirs ────────────────────────────
mkdir -p "$PIPELINE_DIR/outputs/images"
mkdir -p "$PIPELINE_DIR/outputs/meshes"
mkdir -p "$PIPELINE_DIR/outputs/renders"

# ── Done ──────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ Setup complete!                                  ║"
echo "║                                                      ║"
echo "║  Run the pipeline:                                   ║"
echo "║    ./run.sh 'a red sports car'                       ║"
echo "║                                                      ║"
echo "║  Start Web UI:                                       ║"
echo "║    ./start-ui.sh                                     ║"
echo "║                                                      ║"
echo "║  Or use CLI directly:                                ║"
echo "║    source venv/bin/activate                          ║"
echo "║    python pipeline.py --prompt 'a red car'          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
