# 🎨 Stable Diffusion — Local Image Generation

**100% local text-to-image generation on your Mac using Apple Silicon MPS (Metal Performance Shaders).**

No API keys. No cloud. No usage limits. Images stay on your machine.

---

## 🚀 Quick Start

```bash
cd stable-diffusion
bash setup.sh     # First time only — installs dependencies (~2-3 min)
bash start.sh
# Open: http://localhost:5050
```

First generation downloads the model (~2-7 GB). Subsequent runs are instant.

---

## ⚡ Performance (Apple Silicon)

| Model | Size | Speed M1/M2 | Best For |
|-------|------|-------------|---------|
| SDXL-Turbo ⭐ | ~7 GB | **~3–8s** | Default — fastest, great quality |
| SD 2.1 | ~5 GB | ~20–40s | Balanced quality |
| SD 1.5 | ~4 GB | ~15–30s | Classic, wide LoRA support |
| DreamShaper 8 | ~4 GB | ~15–30s | Artistic, fantasy |
| OpenJourney v4 | ~4 GB | ~15–30s | Midjourney-style |
| Realistic Vision 5.1 | ~4 GB | ~15–30s | Photorealistic portraits |

**Memory usage:** ~6–10 GB RAM. Works on 16 GB Mac mini.

---

## 🌐 Web UI Features

- **✨ Generate** — type a prompt, click generate
- **🗂️ History** — browse all generated images
- **📱 Social Post** — generate images for Tax AI Social posts automatically
- Prompt chips — quick style shortcuts
- Size presets: 1:1, 16:9, 9:16, 4:3
- Steps & CFG sliders
- Seed control (fix seed to reproduce results)
- ⌘+Enter keyboard shortcut to generate

---

## 🔌 API

### Generate image
```bash
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "professional tax accountant, modern office, photorealistic 4K",
    "model": "sdxl-turbo",
    "steps": 4,
    "width": 1024,
    "height": 1024,
    "seed": -1
  }'
```

Response:
```json
{
  "success": true,
  "url": "/images/20240322_103045_12345678.png",
  "filename": "20240322_103045_12345678.png",
  "elapsed": 4.2,
  "model": "sdxl-turbo",
  "seed": 12345678,
  "device": "mps"
}
```

### Check status
```bash
curl http://localhost:5050/api/status
```

### List models
```bash
curl http://localhost:5050/api/models
```

---

## 🔗 Tax AI Social Integration

Use `sd_client.py` to generate images from Tax AI Social:

```python
from sd_client import generate_for_post, is_sd_running

if is_sd_running():
    img_url = generate_for_post(
        caption="Tax deadline is April 15th — don't wait!",
        specialty="tax_preparation"
    )
    # img_url = "http://localhost:5050/images/20240322_103045_xxx.png"
```

---

## ⚙️ Environment Variables

```bash
SD_MODEL=sdxl-turbo bash start.sh     # Change default model
SD_PORT=5051 bash start.sh            # Change port
```

---

## 🔒 Privacy

- All generation happens 100% locally
- No internet connection needed after first model download
- Images saved to `./generated/` — delete anytime
- Model weights stored in `~/.cache/huggingface/`

---

## 🛠️ Troubleshooting

**Out of memory on Mac 8GB:**
```bash
SD_MODEL=sd15 bash start.sh    # Use smaller model
# Or reduce size to 512x512 in the UI
```

**Model download fails:**
```bash
# Check HuggingFace connection
curl -I https://huggingface.co
# Try smaller model
SD_MODEL=sd15 bash start.sh
```

**Slow on first run:**
First inference on MPS is slower due to Metal shader compilation — subsequent images are faster.
