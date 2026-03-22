#!/usr/bin/env python3
"""
app.py — Stable Diffusion image generation server
Runs on Apple Silicon (MPS), CUDA, or CPU.
Model: stabilityai/stable-diffusion-2-1 (or SDXL-turbo for speed)

Routes:
  GET  /              → Web UI
  POST /api/generate  → Generate image from prompt
  GET  /api/status    → Check model + device status
  GET  /api/models    → List supported model IDs
  GET  /images/<f>    → Serve generated images
"""

import os
import io
import uuid
import time
import json
import base64
import logging
import threading
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

BASE_DIR   = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "generated"
IMAGES_DIR.mkdir(exist_ok=True)

# ── Model registry ────────────────────────────────────────────────────────────
MODELS = {
    "sd21":       "stabilityai/stable-diffusion-2-1",
    "sdxl-turbo": "stabilityai/sdxl-turbo",
    "sd15":       "runwayml/stable-diffusion-v1-5",
    "dreamshaper": "Lykon/dreamshaper-8",
    "openjourney": "prompthero/openjourney-v4",
    "realistic":   "SG161222/Realistic_Vision_V5.1_noVAE",
}

DEFAULT_MODEL = os.environ.get("SD_MODEL", "sdxl-turbo")

# ── Global pipeline state ─────────────────────────────────────────────────────
_pipe        = None
_pipe_model  = None
_device      = None
_pipe_lock   = threading.Lock()
_load_status = {"loading": False, "loaded": False, "error": None, "model": None, "device": None}


def _get_device():
    import torch
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _load_pipeline(model_id: str):
    """Load (or hot-swap) the Stable Diffusion pipeline."""
    global _pipe, _pipe_model, _device, _load_status

    import torch
    from diffusers import (
        StableDiffusionPipeline,
        StableDiffusionXLPipeline,
        AutoPipelineForText2Image,
    )

    _load_status = {"loading": True, "loaded": False, "error": None, "model": model_id, "device": None}
    device = _get_device()
    log.info(f"Loading model '{model_id}' on device '{device}' ...")

    try:
        repo = MODELS.get(model_id, model_id)
        # MPS must use float32 — float16 causes black/NaN images on Apple Silicon
        dtype = torch.float32 if device == "mps" else (torch.float16 if device == "cuda" else torch.float32)

        # Use AutoPipeline for broad compatibility
        pipe = AutoPipelineForText2Image.from_pretrained(
            repo,
            torch_dtype=dtype,
            variant="fp16" if device == "cuda" else None,
            use_safetensors=True,
        )
        # ── MPS fix: SDXL VAE decode on MPS produces black/NaN images with float16.
        # enable_sequential_cpu_offload() routes UNet on MPS and VAE decode on CPU,
        # completely avoiding the black image bug while keeping GPU acceleration.
        if device == "mps":
            pipe.enable_sequential_cpu_offload()
            log.info("🍎 MPS: sequential_cpu_offload enabled to prevent black image bug")
        elif device == "cuda":
            pipe.to(device)
            pipe.enable_model_cpu_offload()
        else:
            pipe = pipe.to(device)

        _pipe       = pipe
        _pipe_model = model_id
        _device     = device
        _load_status = {"loading": False, "loaded": True, "error": None, "model": model_id, "device": device}
        log.info(f"✅ Model '{model_id}' loaded on {device}")

    except Exception as e:
        _load_status = {"loading": False, "loaded": False, "error": str(e), "model": model_id, "device": device}
        log.error(f"❌ Failed to load model: {e}")


def _ensure_pipeline(model_id: str = DEFAULT_MODEL):
    """Load pipeline if not already loaded, or swap model if different."""
    global _pipe, _pipe_model
    with _pipe_lock:
        if _pipe is None or _pipe_model != model_id:
            _load_pipeline(model_id)
    return _pipe


# ── Startup: pre-load default model in background ─────────────────────────────
def _bg_load():
    _ensure_pipeline(DEFAULT_MODEL)

threading.Thread(target=_bg_load, daemon=True).start()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_file(str(BASE_DIR / "index.html"))


@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(str(IMAGES_DIR), filename)


@app.route("/api/status")
def api_status():
    return jsonify(_load_status)


@app.route("/api/models")
def api_models():
    return jsonify({"models": list(MODELS.keys()), "descriptions": MODELS, "default": DEFAULT_MODEL})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """
    POST /api/generate
    Body:
      prompt         (str)  required
      negative_prompt (str) optional
      model          (str)  optional, default sdxl-turbo
      steps          (int)  optional, default 4 (turbo) / 20 (sd)
      guidance       (float) optional, CFG scale, default 0 for turbo
      width          (int)  optional, default 1024
      height         (int)  optional, default 1024
      seed           (int)  optional, -1 = random
      format         (str)  "url" | "base64" | "both" — default "url"
    """
    import torch

    data   = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"success": False, "error": "prompt is required"}), 400

    model_id        = data.get("model",           DEFAULT_MODEL)
    negative_prompt = data.get("negative_prompt", "blurry, ugly, distorted, watermark, text, nsfw")
    steps           = int(data.get("steps",       4 if "turbo" in model_id else 20))
    guidance        = float(data.get("guidance",  0.0 if "turbo" in model_id else 7.5))
    width           = int(data.get("width",       1024))
    height          = int(data.get("height",      1024))
    seed            = int(data.get("seed",        -1))
    fmt             = data.get("format",          "url")   # url | base64 | both

    # Load / swap model
    if _load_status["loading"]:
        return jsonify({"success": False, "error": "Model is still loading, please wait..."}), 503

    pipe = _ensure_pipeline(model_id)
    if pipe is None:
        return jsonify({"success": False, "error": _load_status.get("error", "Pipeline not loaded")}), 500

    # Seed — use CPU generator when sequential_cpu_offload is active (MPS)
    # because offloaded pipelines route through CPU
    gen_device = "cpu" if _device == "mps" else _device
    generator = None
    if seed != -1:
        generator = torch.Generator(device=gen_device).manual_seed(seed)
    else:
        seed = torch.randint(0, 2**32, (1,)).item()
        generator = torch.Generator(device=gen_device).manual_seed(seed)

    log.info(f"Generating: '{prompt[:80]}' model={model_id} steps={steps} size={width}x{height} seed={seed}")
    t0 = time.time()

    try:
        with _pipe_lock:
            kwargs = dict(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=steps,
                width=width,
                height=height,
                generator=generator,
            )
            # guidance_scale=0 means turbo mode (no CFG)
            if guidance > 0:
                kwargs["guidance_scale"] = guidance

            result = pipe(**kwargs)
            image = result.images[0]

    except Exception as e:
        log.error(f"Generation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    elapsed = round(time.time() - t0, 2)

    # Save to disk
    filename  = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{seed}.png"
    save_path = IMAGES_DIR / filename
    image.save(str(save_path), format="PNG")

    response = {
        "success":  True,
        "filename": filename,
        "prompt":   prompt,
        "model":    model_id,
        "steps":    steps,
        "seed":     seed,
        "width":    width,
        "height":   height,
        "elapsed":  elapsed,
        "device":   _device,
    }

    if fmt in ("url", "both"):
        response["url"] = f"/images/{filename}"

    if fmt in ("base64", "both"):
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        response["base64"] = base64.b64encode(buf.getvalue()).decode("utf-8")

    log.info(f"✅ Generated in {elapsed}s → {filename}")
    return jsonify(response)


@app.route("/api/history")
def api_history():
    """Return list of recently generated images."""
    images = sorted(IMAGES_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    limit  = int(request.args.get("limit", 50))
    return jsonify({
        "images": [
            {"filename": p.name, "url": f"/images/{p.name}", "size": p.stat().st_size,
             "created": datetime.fromtimestamp(p.stat().st_mtime).isoformat()}
            for p in images[:limit]
        ]
    })


@app.route("/api/delete/<filename>", methods=["DELETE"])
def api_delete(filename):
    """Delete a generated image."""
    path = IMAGES_DIR / filename
    if path.exists() and path.parent == IMAGES_DIR:
        path.unlink()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Not found"}), 404


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════╗
║   🎨 Stable Diffusion — Local Image Generator  ║
║   Open: http://localhost:5050                  ║
║   Model: """ + DEFAULT_MODEL + """
╚══════════════════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=5050, debug=False)
