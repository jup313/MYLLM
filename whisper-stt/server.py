"""
Local Whisper STT Server
========================
Runs on http://localhost:9000
Exposes /v1/audio/transcriptions (OpenAI-compatible format)
Open WebUI connects to it directly — 100% private, nothing leaves your Mac.

Uses: faster-whisper (optimized Whisper for CPU/Apple Silicon)
"""

import os
import tempfile
import time
from flask import Flask, request, jsonify
from faster_whisper import WhisperModel

app = Flask(__name__)

# Model size options: tiny, base, small, medium
# "small" is recommended — ~500MB RAM, very accurate
MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")
DEVICE = "cpu"         # Apple Silicon uses CPU for faster-whisper (still fast!)
COMPUTE_TYPE = "int8"  # Fastest + lowest memory on Mac

print(f"🎙️  Loading Whisper model: {MODEL_SIZE} ...")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print(f"✅ Whisper model loaded! Ready at http://localhost:9000")

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "running",
        "model": MODEL_SIZE,
        "device": DEVICE,
        "endpoints": ["/v1/audio/transcriptions", "/health"]
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL_SIZE})

@app.route("/v1/audio/transcriptions", methods=["POST"])
def transcribe():
    """
    OpenAI-compatible transcription endpoint.
    Open WebUI sends audio here as multipart/form-data.
    """
    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["file"]
    language = request.form.get("language", None)  # Optional language hint

    # Save to temp file
    suffix = os.path.splitext(audio_file.filename or "audio.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        start = time.time()
        segments, info = model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,           # Remove silence
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        text = " ".join([seg.text for seg in segments]).strip()
        elapsed = round(time.time() - start, 2)

        print(f"🎤 Transcribed in {elapsed}s: {text[:80]}...")

        # OpenAI-compatible response format
        return jsonify({
            "text": text,
            "language": info.language,
            "duration": info.duration
        })

    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 9000))
    print(f"\n🎙️  Whisper STT Server starting on http://localhost:{port}")
    print(f"📌 Set in Open WebUI: Settings → Audio → STT → OpenAI API")
    print(f"   Base URL: http://localhost:{port}/v1")
    print(f"   API Key: any value (e.g. 'local')\n")
    app.run(host="0.0.0.0", port=port, debug=False)
