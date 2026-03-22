import requests
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

def generate_from_llm(prompt, max_tokens=600):
    """Call Ollama local LLM and return generated text."""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.75,
                    "top_p": 0.9
                }
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "❌ Cannot connect to Ollama. Make sure it's running:\n"
            "  ollama serve\n"
            "Then try again."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("❌ Ollama timed out. The model may be loading — try again in 30 seconds.")
    except Exception as e:
        raise RuntimeError(f"❌ LLM error: {str(e)}")

def check_ollama_status():
    """Check if Ollama is running and the model is available."""
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        model_available = any(OLLAMA_MODEL in m for m in models)
        return {"running": True, "model_available": model_available, "models": models}
    except Exception:
        return {"running": False, "model_available": False, "models": []}
