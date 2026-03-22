# 🎙️ Local Whisper STT Server

**100% private speech-to-text for Open WebUI — nothing leaves your Mac.**

Uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — OpenAI's Whisper model optimized for CPU/Apple Silicon. Exposes an OpenAI-compatible API so Open WebUI connects to it directly.

---

## ⚡ Quick Start

```bash
cd whisper-stt
bash start.sh
```

First run automatically:
1. Creates a Python virtual environment
2. Installs `faster-whisper` + `flask`
3. Downloads the Whisper `small` model (~460 MB, one time)
4. Starts server on **http://localhost:9000**

---

## 🔧 Connect to Open WebUI

1. Open **http://localhost:3000**
2. Click your **profile icon** (top right) → **Settings**
3. Go to **Audio** tab
4. Under **Speech to Text (STT)**:
   - Engine: **OpenAI API**
   - Base URL: `http://localhost:9000/v1`
   - API Key: `local` (any value works)
5. Save

Now click the **🎤 microphone** in the chat input — it will use your local Whisper!

---

## 🧠 Model Options

Change the model in `start.sh` by setting `WHISPER_MODEL`:

```bash
WHISPER_MODEL=tiny bash start.sh    # ~75MB  — fastest, less accurate
WHISPER_MODEL=base bash start.sh    # ~145MB — good for English
WHISPER_MODEL=small bash start.sh   # ~460MB — best for Mac 16GB ✅ (default)
WHISPER_MODEL=medium bash start.sh  # ~1.5GB — most accurate, slower
```

**Recommendation for Mac 16GB:** `small` — transcribes 10 seconds of audio in ~1 second.

---

## 📡 API Endpoint

```
POST http://localhost:9000/v1/audio/transcriptions
Content-Type: multipart/form-data

file: <audio file>  (webm, mp3, wav, m4a, ogg)
language: en        (optional — auto-detects if not set)
```

Response (OpenAI-compatible):
```json
{
  "text": "Your transcribed speech here",
  "language": "en",
  "duration": 3.42
}
```

Check health:
```bash
curl http://localhost:9000/health
```

---

## 🔒 Privacy

- Audio is processed **entirely on your Mac** — never uploaded anywhere
- The Whisper model runs locally via `faster-whisper`
- No API keys required
- Works offline after first setup

---

## 🖥️ Memory Usage

| Model | RAM | Speed (10s audio) |
|-------|-----|-------------------|
| tiny | ~150 MB | ~0.3s |
| base | ~250 MB | ~0.5s |
| small | ~500 MB | ~1s ✅ |
| medium | ~1.5 GB | ~3s |

---

## 🛑 Stop the server

Press `Ctrl+C` in the terminal running `start.sh`.
