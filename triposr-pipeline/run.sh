#!/bin/bash
# ─────────────────────────────────────────────────────────────
# run.sh  —  Quick CLI launcher for TripoSR Pipeline
# Usage:
#   ./run.sh "a red sports car"
#   ./run.sh "a medieval castle" --steps 30
#   ./run.sh --image /path/to/photo.jpg
# ─────────────────────────────────────────────────────────────

PIPELINE_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$PIPELINE_DIR/venv"

# Check venv exists
if [ ! -d "$VENV" ]; then
    echo ""
    echo "❌ Virtual environment not found."
    echo "   Run setup first:  ./setup.sh"
    echo ""
    exit 1
fi

source "$VENV/bin/activate"

# First argument as idea (unless it starts with --)
if [ $# -eq 0 ]; then
    echo ""
    echo "Usage: ./run.sh \"your idea\"  [options]"
    echo ""
    echo "Options:"
    echo "  --model    mistral:7b       (Ollama model)"
    echo "  --steps    20               (SD inference steps)"
    echo "  --mc-res   256              (mesh resolution)"
    echo "  --skip-llm                  (use idea directly as SD prompt)"
    echo "  --image    /path/img.png    (skip SD, use existing image)"
    echo ""
    echo "Examples:"
    echo "  ./run.sh \"a wooden chair\""
    echo "  ./run.sh \"a cute robot\" --steps 30 --mc-res 384"
    echo "  ./run.sh --image ~/Downloads/my_object.jpg"
    echo ""
    exit 0
fi

# If first arg doesn't start with --, treat as --idea
if [[ "$1" != --* ]]; then
    IDEA="$1"
    shift
    python3 "$PIPELINE_DIR/pipeline.py" --idea "$IDEA" "$@"
else
    python3 "$PIPELINE_DIR/pipeline.py" "$@"
fi
