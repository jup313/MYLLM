#!/usr/bin/env python3
"""
TripoSR Pipeline — Web UI
Flask-based web interface for the full pipeline.
Run: python app.py  →  open http://localhost:5050
"""

import os
import sys
import json
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

# ── Import pipeline functions ────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from pipeline import run_pipeline, llm_generate_prompt

PIPELINE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR   = PIPELINE_DIR / "outputs"
STATIC_DIR   = PIPELINE_DIR / "static"

app  = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
CORS(app)

# ── Job tracking ─────────────────────────────────────────────
jobs = {}

def run_job(job_id: str, kwargs: dict):
    """Run pipeline in background thread."""
    jobs[job_id]["status"] = "running"
    try:
        result = run_pipeline(**kwargs)
        jobs[job_id]["status"] = "done"
        jobs[job_id]["result"] = result
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"]  = str(e)


# ── API Routes ───────────────────────────────────────────────

@app.route("/")
def index():
    return send_file(PIPELINE_DIR / "index.html")

@app.route("/api/generate-prompt", methods=["POST"])
def api_generate_prompt():
    """Stage 1 only: idea → SD prompt via Ollama."""
    data  = request.json or {}
    idea  = data.get("idea", "")
    model = data.get("model", "mistral:7b")
    if not idea:
        return jsonify({"error": "idea required"}), 400
    try:
        prompt = llm_generate_prompt(idea, model=model)
        return jsonify({"prompt": prompt})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/pipeline", methods=["POST"])
def api_pipeline():
    """Start full pipeline job (async)."""
    import uuid
    data = request.json or {}

    idea         = data.get("idea")
    image        = data.get("image")
    model        = data.get("model",    "mistral:7b")
    steps        = int(data.get("steps", 20))
    mc_resolution = int(data.get("mc_resolution", 256))
    skip_llm     = bool(data.get("skip_llm", False))

    if not idea and not image:
        return jsonify({"error": "idea or image required"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "queued", "result": None, "error": None}

    thread = threading.Thread(
        target=run_job,
        args=(job_id, {
            "idea": idea, "image": image, "model": model,
            "steps": steps, "mc_resolution": mc_resolution,
            "skip_llm": skip_llm
        }),
        daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id, "status": "queued"})

@app.route("/api/job/<job_id>")
def api_job_status(job_id: str):
    """Check job status."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)

@app.route("/api/outputs")
def api_outputs():
    """List all generated outputs."""
    images = sorted(
        (OUTPUT_DIR / "images").glob("*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    ) if (OUTPUT_DIR / "images").exists() else []

    meshes = sorted(
        (OUTPUT_DIR / "meshes").rglob("*.glb"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    ) if (OUTPUT_DIR / "meshes").exists() else []

    return jsonify({
        "images": [str(p.relative_to(PIPELINE_DIR)) for p in images[:20]],
        "meshes": [str(p.relative_to(PIPELINE_DIR)) for p in meshes[:20]]
    })

@app.route("/outputs/<path:filepath>")
def serve_output(filepath):
    """Serve output files (images, meshes)."""
    return send_from_directory(str(OUTPUT_DIR), filepath)

@app.route("/api/models")
def api_models():
    """List available Ollama models."""
    import requests as req
    try:
        r = req.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        return jsonify({"models": models})
    except Exception:
        return jsonify({"models": ["mistral:7b", "deepseek-coder:6.7b"]})


if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║   🧊 TripoSR Web UI                             ║")
    print("║   Open: http://localhost:5050                   ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
