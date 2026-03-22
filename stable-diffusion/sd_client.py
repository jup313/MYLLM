"""
sd_client.py — Python client for the Stable Diffusion server
Use this in other services (e.g. Tax AI Social) to generate images.

Usage:
    from sd_client import generate_image, is_sd_running

    url = generate_image("professional tax accountant, modern office, photorealistic")
    # Returns: "http://localhost:5050/images/20240322_103045_12345678.png" or None
"""

import requests
from typing import Optional

SD_BASE_URL = "http://localhost:5050"

# ── Social media style presets ────────────────────────────────────────────────
STYLE_PRESETS = {
    "business": "professional business photo, office setting, tax documents, calculator, modern clean design, photorealistic, 4K",
    "family":   "warm family home, tax documents, financial security, smiling people, photorealistic",
    "irs":      "IRS debt relief, financial freedom, professional accountant, calm and confident, illustration",
    "savings":  "money savings, green dollars, piggy bank, happy, vibrant colors, financial success",
    "deadline": "tax deadline, calendar, urgency, professional help, modern office, photorealistic",
    "books":    "bookkeeping, organized finances, clean desk, spreadsheets, modern office, photorealistic",
    "default":  "professional tax and accounting marketing image, clean modern design, photorealistic, 4K",
}


def is_sd_running(timeout: float = 2.0) -> bool:
    """Return True if Stable Diffusion server is up and model is loaded."""
    try:
        r = requests.get(f"{SD_BASE_URL}/api/status", timeout=timeout)
        d = r.json()
        return d.get("loaded", False)
    except Exception:
        return False


def generate_image(
    prompt: str,
    style: str = "default",
    negative_prompt: str = "blurry, ugly, distorted, watermark, text, nsfw, low quality",
    model: str = "sdxl-turbo",
    steps: int = 4,
    width: int = 1024,
    height: int = 1024,
    seed: int = -1,
    timeout: float = 120.0,
) -> Optional[str]:
    """
    Generate an image and return its full URL (or None on failure).

    Args:
        prompt:          Image description
        style:           One of STYLE_PRESETS keys (prepended to prompt)
        negative_prompt: Things to avoid
        model:           Model ID (sdxl-turbo, sd21, sd15, dreamshaper, openjourney, realistic)
        steps:           Inference steps (4 for turbo, 20 for others)
        width/height:    Image dimensions
        seed:            -1 for random
        timeout:         HTTP timeout in seconds

    Returns:
        Full URL string like "http://localhost:5050/images/filename.png"
        or None on failure.
    """
    # Combine style preset + custom prompt
    style_prefix = STYLE_PRESETS.get(style, STYLE_PRESETS["default"])
    full_prompt   = f"{style_prefix}, {prompt}" if prompt else style_prefix

    try:
        r = requests.post(
            f"{SD_BASE_URL}/api/generate",
            json={
                "prompt":          full_prompt,
                "negative_prompt": negative_prompt,
                "model":           model,
                "steps":           steps,
                "guidance":        0.0 if "turbo" in model else 7.5,
                "width":           width,
                "height":          height,
                "seed":            seed,
                "format":          "url",
            },
            timeout=timeout,
        )
        d = r.json()
        if d.get("success"):
            return f"{SD_BASE_URL}{d['url']}"
        else:
            print(f"[sd_client] Generation failed: {d.get('error')}")
            return None
    except Exception as e:
        print(f"[sd_client] Error: {e}")
        return None


def generate_for_post(caption: str, specialty: str = "tax_preparation") -> Optional[str]:
    """
    Convenience wrapper for Tax AI Social posts.
    Picks the right style based on specialty and caption keywords.

    Args:
        caption:   The post caption text
        specialty: "tax_preparation" | "tax_resolution" | "bookkeeping"

    Returns:
        Full image URL or None
    """
    caption_lower = caption.lower()

    # Pick style based on content
    if specialty == "tax_resolution" or any(w in caption_lower for w in ["irs", "debt", "relief", "settlement", "offer in compromise"]):
        style = "irs"
    elif specialty == "bookkeeping" or any(w in caption_lower for w in ["bookkeeping", "books", "records", "accounting"]):
        style = "books"
    elif any(w in caption_lower for w in ["save", "saving", "refund", "money back", "return"]):
        style = "savings"
    elif any(w in caption_lower for w in ["deadline", "april", "due date", "last day", "hurry"]):
        style = "deadline"
    elif any(w in caption_lower for w in ["family", "household", "dependent", "child", "home"]):
        style = "family"
    else:
        style = "business"

    # Extract a few key words from caption to personalize the prompt
    keywords = [
        w for w in caption.replace("\n", " ").split()
        if len(w) > 4 and w.isalpha()
    ][:6]
    extra = ", ".join(keywords) if keywords else ""

    return generate_image(prompt=extra, style=style)
