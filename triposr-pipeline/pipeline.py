#!/usr/bin/env python3
"""
TripoSR Full Pipeline for Apple Silicon Mac (16GB)
─────────────────────────────────────────────────
Pipeline stages:
  1. LLM (Ollama/mistral:7b) → Generate image prompt from idea
  2. Stable Diffusion (diffusers, MPS) → Generate image from prompt
  3. TripoSR → Convert image to 3D mesh (OBJ / GLB)
  4. Save outputs to ./outputs/

Usage:
  python pipeline.py --idea "a medieval castle"
  python pipeline.py --idea "a futuristic robot" --model mistral:7b
  python pipeline.py --image path/to/image.png  # skip SD step
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime

# ── Paths ───────────────────────────────────────────────────
PIPELINE_DIR = Path(__file__).parent.resolve()
OUTPUT_IMAGES = PIPELINE_DIR / "outputs" / "images"
OUTPUT_MESHES = PIPELINE_DIR / "outputs" / "meshes"
TRIPOSR_DIR   = PIPELINE_DIR / "TripoSR"

# Create output directories
OUTPUT_IMAGES.mkdir(parents=True, exist_ok=True)
OUTPUT_MESHES.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = "http://localhost:11434"


# ══════════════════════════════════════════════════════════════
# STAGE 1 — LLM: Idea → Optimized Image Prompt
# ══════════════════════════════════════════════════════════════

def llm_generate_prompt(idea: str, model: str = "mistral:7b") -> str:
    """
    Use Ollama to convert a free-form idea into an optimized
    Stable Diffusion prompt suitable for TripoSR.
    """
    print(f"\n🧠 [Stage 1] Generating SD prompt from idea: '{idea}'")
    print(f"   Model: {model}")

    system = (
        "You are an expert at writing Stable Diffusion prompts for 3D model generation. "
        "Create a single-object prompt optimized for TripoSR 3D reconstruction. "
        "Rules: "
        "1. Single object, centered, white/neutral background "
        "2. Include: object type, material, style, lighting keywords "
        "3. Add: 'white background, studio lighting, 4K, product shot, isolated' "
        "4. Keep under 75 tokens "
        "5. Return ONLY the prompt, no explanation."
    )

    user_msg = f"Create a Stable Diffusion prompt for: {idea}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg}
        ],
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 150}
    }

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        prompt = data["message"]["content"].strip().strip('"')
        print(f"   ✅ Generated prompt: {prompt}")
        return prompt
    except Exception as e:
        print(f"   ⚠️  Ollama failed ({e}), using fallback prompt")
        return (
            f"{idea}, white background, studio lighting, "
            "4K, product shot, isolated, single object"
        )


# ══════════════════════════════════════════════════════════════
# STAGE 2 — Stable Diffusion: Prompt → Image
# ══════════════════════════════════════════════════════════════

def sd_generate_image(prompt: str, output_path: Path, steps: int = 20) -> Path:
    """
    Generate an image using Stable Diffusion on Apple MPS.
    Uses stabilityai/stable-diffusion-2-1-base (good for 16GB).
    """
    print(f"\n🎨 [Stage 2] Generating image with Stable Diffusion...")
    print(f"   Prompt: {prompt[:80]}...")
    print(f"   Steps: {steps}")

    import torch
    from diffusers import StableDiffusionPipeline, EulerAncestralDiscreteScheduler

    # Pick device
    if torch.backends.mps.is_available():
        device = "mps"
        dtype  = torch.float16
        print("   🍎 Using Apple MPS (Metal)")
    elif torch.cuda.is_available():
        device = "cuda"
        dtype  = torch.float16
        print("   🟢 Using CUDA GPU")
    else:
        device = "cpu"
        dtype  = torch.float32
        print("   💻 Using CPU (slow)")

    # SD 1.5 — ~4GB, fully public, no auth required
    # (runwayml repo was migrated to new org stable-diffusion-v1-5)
    model_id = "stable-diffusion-v1-5/stable-diffusion-v1-5"
    print(f"   Loading model: {model_id}")
    print("   (First run downloads ~4GB — subsequent runs use cache)")

    import os
    os.environ["HUGGINGFACE_HUB_VERBOSITY"] = "warning"

    sd_pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=dtype,
        safety_checker=None,    # disable for speed
        requires_safety_checker=False,
        token=False             # fully public model — no auth needed
    )
    sd_pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(
        sd_pipe.scheduler.config
    )
    sd_pipe = sd_pipe.to(device)

    if device == "mps":
        sd_pipe.enable_attention_slicing()   # reduce MPS memory pressure

    negative_prompt = (
        "blurry, multiple objects, background clutter, shadows, "
        "low quality, bad anatomy, extra objects"
    )

    print("   Generating... (this takes ~30–90 seconds on Apple Silicon)")
    t0 = time.time()

    with torch.inference_mode():
        result = sd_pipe(
            prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=steps,
            guidance_scale=7.5,
            width=512,
            height=512
        )

    image = result.images[0]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(output_path))
    elapsed = time.time() - t0
    print(f"   ✅ Image saved: {output_path} ({elapsed:.1f}s)")

    # Free VRAM
    del sd_pipe
    if device == "mps":
        import gc
        gc.collect()
        torch.mps.empty_cache()

    return output_path


# ══════════════════════════════════════════════════════════════
# STAGE 3 — TripoSR: Image → 3D Mesh
# ══════════════════════════════════════════════════════════════

def triposr_generate_mesh(
    image_path: Path,
    output_dir: Path,
    mc_resolution: int = 256
) -> Path:
    """
    Run TripoSR to convert a single image to a 3D mesh.
    Returns path to the output OBJ file.
    """
    print(f"\n🧊 [Stage 3] Running TripoSR 3D reconstruction...")
    print(f"   Input:  {image_path}")
    print(f"   Output: {output_dir}")
    print(f"   Marching cubes resolution: {mc_resolution}")

    import torch
    import numpy as np
    from PIL import Image

    # Add TripoSR to path
    if str(TRIPOSR_DIR) not in sys.path:
        sys.path.insert(0, str(TRIPOSR_DIR))

    try:
        from tsr.system import TSR
        from tsr.utils import remove_background, resize_foreground
    except ImportError as e:
        print(f"   ❌ TripoSR not found: {e}")
        print(f"   Run setup.sh first!")
        raise

    # Device selection
    if torch.backends.mps.is_available():
        device = "mps"
        print("   🍎 Using Apple MPS")
    elif torch.cuda.is_available():
        device = "cuda"
        print("   🟢 Using CUDA")
    else:
        device = "cpu"
        print("   💻 Using CPU")

    # Load TripoSR model
    print("   Loading TripoSR model (stabilityai/TripoSR ~1GB)...")
    print("   (First run downloads model — cached after)")

    model = TSR.from_pretrained(
        "stabilityai/TripoSR",
        config_name="config.yaml",
        weight_name="model.ckpt"
    )
    model.renderer.set_chunk_size(8192)
    model.to(device)

    # Load and preprocess image
    print("   Preprocessing image...")
    image = Image.open(str(image_path)).convert("RGBA")

    # Remove background (rembg)
    image = remove_background(image)
    image = resize_foreground(image, 0.85)

    # Normalize to RGB with white background
    img_array = np.array(image).astype(np.float32) / 255.0
    img_rgb = img_array[:, :, :3]
    alpha   = img_array[:, :, 3:4]
    img_rgb = img_rgb * alpha + (1 - alpha)  # white bg
    image = Image.fromarray((img_rgb * 255).astype(np.uint8))

    # Run TripoSR inference
    print("   Running TripoSR inference...")
    t0 = time.time()
    with torch.no_grad():
        scene_codes = model([image], device=device)

    # Extract mesh via marching cubes
    # has_vertex_color=False is standard for TripoSR (no per-vertex color)
    print(f"   Extracting mesh (mc_resolution={mc_resolution})...")
    meshes = model.extract_mesh(scene_codes, has_vertex_color=False, resolution=mc_resolution)
    elapsed = time.time() - t0
    print(f"   ✅ Mesh extracted in {elapsed:.1f}s")

    # Export mesh files
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Export OBJ
    obj_path = output_dir / f"mesh_{timestamp}.obj"
    meshes[0].export(str(obj_path))
    print(f"   ✅ OBJ saved: {obj_path}")

    # Export GLB
    glb_path = output_dir / f"mesh_{timestamp}.glb"
    meshes[0].export(str(glb_path))
    print(f"   ✅ GLB saved: {glb_path}")

    # Free memory
    del model
    if device == "mps":
        import gc
        gc.collect()
        torch.mps.empty_cache()

    return obj_path


# ══════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════

def run_pipeline(
    idea:          str  = None,
    image:         str  = None,
    model:         str  = "mistral:7b",
    steps:         int  = 20,
    mc_resolution: int  = 256,
    skip_llm:      bool = False,
    skip_sd:       bool = False
):
    """Run the full LLM → SD → TripoSR pipeline."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print("\n" + "═" * 60)
    print("  🚀 TripoSR Pipeline — Apple Silicon Mac")
    print("═" * 60)

    # ── Stage 1: LLM ────────────────────────────────────────
    sd_prompt = None
    if image:
        image_path = Path(image)
        print(f"\n📁 Using provided image: {image_path}")
        skip_sd = True
    elif skip_llm and idea:
        sd_prompt = idea
        print(f"\n⏭️  Skipping LLM, using raw prompt: {sd_prompt}")
    elif idea:
        sd_prompt = llm_generate_prompt(idea, model=model)
    else:
        raise ValueError("Provide --idea or --image")

    # ── Stage 2: Stable Diffusion ───────────────────────────
    if not skip_sd:
        img_filename = f"sd_{timestamp}.png"
        image_path = OUTPUT_IMAGES / img_filename
        image_path = sd_generate_image(sd_prompt, image_path, steps=steps)
    else:
        image_path = Path(image) if image else image_path

    print(f"\n   📸 Input image: {image_path}")

    # ── Stage 3: TripoSR ────────────────────────────────────
    mesh_dir = OUTPUT_MESHES / timestamp
    obj_path = triposr_generate_mesh(
        image_path,
        mesh_dir,
        mc_resolution=mc_resolution
    )

    # ── Summary ─────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  ✅ Pipeline Complete!")
    print("═" * 60)
    if sd_prompt:
        print(f"  Prompt:    {sd_prompt[:70]}...")
    print(f"  Image:     {image_path}")
    print(f"  OBJ Mesh:  {obj_path}")
    print(f"  GLB Mesh:  {str(obj_path).replace('.obj', '.glb')}")
    print(f"  Folder:    {mesh_dir}")
    print()
    print("  💡 Open the .glb in Quick Look (space bar) or")
    print("     drag the .obj into Blender!")
    print("═" * 60)
    print()

    return {
        "image": str(image_path),
        "obj":   str(obj_path),
        "glb":   str(obj_path).replace(".obj", ".glb"),
        "dir":   str(mesh_dir)
    }


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="TripoSR Pipeline: LLM → Stable Diffusion → 3D Mesh",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py --idea "a red sports car"
  python pipeline.py --idea "a medieval castle" --model mistral:7b
  python pipeline.py --idea "a wooden chair" --steps 30 --mc-res 384
  python pipeline.py --image my_photo.jpg           # skip SD
  python pipeline.py --idea "a dragon" --skip-llm   # use raw as SD prompt
        """
    )
    parser.add_argument("--idea",     type=str, help="Natural language description of what to 3D-ify")
    parser.add_argument("--image",    type=str, help="Path to existing image (skips SD generation)")
    parser.add_argument("--model",    type=str, default="mistral:7b", help="Ollama model (default: mistral:7b)")
    parser.add_argument("--steps",    type=int, default=20, help="SD inference steps (default: 20)")
    parser.add_argument("--mc-res",   type=int, default=256, dest="mc_resolution",
                        help="Marching cubes resolution (default: 256, higher=finer mesh)")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM, use --idea directly as SD prompt")
    parser.add_argument("--skip-sd",  action="store_true", help="Skip SD (requires --image)")

    args = parser.parse_args()

    if not args.idea and not args.image:
        parser.print_help()
        sys.exit(1)

    run_pipeline(
        idea=args.idea,
        image=args.image,
        model=args.model,
        steps=args.steps,
        mc_resolution=args.mc_resolution,
        skip_llm=args.skip_llm,
        skip_sd=args.skip_sd
    )


if __name__ == "__main__":
    main()
