# 🧊 TripoSR 3D Pipeline — Apple Silicon Mac (16GB)

![Architecture](architecture.svg)

Convert any idea into a 3D mesh using a fully local pipeline:

```
💡 Your Idea
     │
     ▼
🧠 Ollama LLM (mistral:7b)
     │  → Generates optimized Stable Diffusion prompt
     ▼
🎨 Stable Diffusion 1.5 (Apple MPS)
     │  → Generates 512×512 product-style image
     ▼
🧊 TripoSR (stabilityai/TripoSR)
     │  → Reconstructs 3D mesh from single image
     ▼
📦 OBJ + GLB output files
```

## 🖥️ Requirements

| Component | Version |
|-----------|---------|
| macOS     | Apple Silicon (M1/M2/M3/M4) |
| RAM       | 16 GB (minimum) |
| Python    | 3.11+ (installed via Homebrew) |
| Ollama    | Running locally |
| Models    | mistral:7b (already installed) |

## 🚀 Quick Start

### Step 1 — Setup (one time)
```bash
cd ~/Desktop/triposr-pipeline
chmod +x setup.sh run.sh start-ui.sh
./setup.sh
```

**What setup.sh installs:**
- Python 3.11 virtual environment
- PyTorch (Apple MPS support)
- Stable Diffusion 1.5 via HuggingFace Diffusers
- TripoSR from GitHub (VAST-AI-Research)
- Flask web UI

**Downloads on first run:**
- Stable Diffusion 1.5 base — ~4 GB (cached)
- TripoSR model — ~1 GB (cached)

---

### Step 2A — CLI Usage
```bash
# Basic usage
./run.sh "a shiny red sports car"

# More options
./run.sh "a medieval stone castle" --steps 30 --mc-res 384

# Skip LLM, use your text directly as SD prompt
./run.sh "red sports car, white background, studio lighting" --skip-llm

# Use your own image (skip SD generation)
./run.sh --image ~/Downloads/my_photo.jpg

# Full options
python3 pipeline.py --idea "a wooden chair" \
    --model mistral:7b \
    --steps 25 \
    --mc-res 256
```

### Step 2B — Web UI
```bash
./start-ui.sh
# Opens http://localhost:5050 automatically
```

---

## 📁 Output Files

All outputs are saved in `./outputs/`:

```
outputs/
├── images/
│   └── sd_20250321_143022.png    ← SD generated image
└── meshes/
    └── 20250321_143022/
        ├── mesh_20250321_143045.obj   ← 3D mesh (Blender, etc.)
        └── mesh_20250321_143045.glb   ← 3D mesh (Quick Look, AR)
```

### View your 3D models:
- **Quick Look** — Press `Space` on any `.glb` file
- **Blender** — File → Import → OBJ / glTF
- **Reality Composer** — For AR on iPhone/iPad
- **Xcode** — Drag `.usdz` (convert with Reality Converter)

---

## ⚙️ Pipeline Options

| Flag | Default | Description |
|------|---------|-------------|
| `--idea` | — | Natural language description |
| `--image` | — | Use existing image (skips SD) |
| `--model` | `mistral:7b` | Ollama model for prompt generation |
| `--steps` | `20` | SD inference steps (higher = better/slower) |
| `--mc-res` | `256` | Marching cubes resolution (higher = finer mesh) |
| `--skip-llm` | off | Use `--idea` text directly as SD prompt |
| `--skip-sd` | off | Skip SD (requires `--image`) |

---

## 💡 Tips for Best Results

### Good ideas for TripoSR:
- ✅ Single objects: cars, chairs, cups, robots, animals, buildings
- ✅ Objects with clear silhouettes work best
- ✅ "product shot" style images = better 3D

### SD Prompt tips:
- Add `white background, studio lighting, isolated` for cleaner meshes
- Avoid complex scenes with multiple objects
- `product shot, 4K` keywords help quality

### Memory management (16GB Mac):
- Default settings (steps=20, mc-res=256) use ~8-10GB
- For `mc-res=384` or higher, close other apps
- SD and TripoSR share memory — pipeline frees each model after use

---

## 🐛 Troubleshooting

### "TripoSR not found"
```bash
./setup.sh  # Re-run setup
```

### Slow on first run
Normal! First run downloads ~6GB of models. Subsequent runs are fast.

### MPS out of memory
```bash
# Use lower resolution
./run.sh "your idea" --steps 15 --mc-res 128
```

### Ollama not responding
```bash
ollama serve &
ollama list   # should show mistral:7b
```

---

## 📦 Project Structure

```
triposr-pipeline/
├── README.md          # This file
├── setup.sh           # One-time setup script
├── run.sh             # CLI pipeline launcher
├── start-ui.sh        # Web UI launcher
├── pipeline.py        # Core pipeline (LLM → SD → TripoSR)
├── app.py             # Flask web server
├── index.html         # Web UI frontend
├── venv/              # Python virtual environment (created by setup.sh)
├── TripoSR/           # TripoSR repo (cloned by setup.sh)
└── outputs/
    ├── images/        # Generated SD images
    └── meshes/        # Generated 3D meshes (OBJ + GLB)
```

---

## 🔗 References

- [TripoSR](https://github.com/VAST-AI-Research/TripoSR) — VAST-AI-Research
- [stabilityai/TripoSR](https://huggingface.co/stabilityai/TripoSR) — HuggingFace model
- [Stable Diffusion 2.1](https://huggingface.co/stabilityai/stable-diffusion-2-1-base)
- [Ollama](https://ollama.com) — Local LLM runner
- [Apple MPS Backend](https://pytorch.org/docs/stable/notes/mps.html) — Metal Performance Shaders
