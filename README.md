<div align="center">

![MyLLM Banner](banner.svg)

</div>

# 🤖 MyLLM – Personal AI Stack on Your Mac

> Run a complete private AI ecosystem locally using **Ollama**, **Open WebUI**, and purpose-built tools for email, finance, 3D generation, image generation, speech-to-text, and social media marketing. **No cloud. No subscriptions. No data leaving your machine.**

<div align="center">

![Architecture](triposr-pipeline/architecture.svg)

</div>

---

## 🧰 Tools in This Stack

| Tool | Purpose | Port |
|------|---------|------|
| 💬 **Open WebUI + SearXNG** | Chat UI with private web search | :3000 / :8080 |
| 📈 **Quant AI** | Stock & crypto analysis + portfolio tracker | :8000 |
| 📧 **Mail AI Manager** | AI email classifier for any IMAP provider (Gmail, iCloud, Outlook, ProtonMail) — 100% local, no Gmail API | :5051 |
| 🎨 **Stable Diffusion** | Local text-to-image generation · Apple Silicon MPS | :5050 |
| 🧊 **TripoSR 3D Pipeline** | Image → 3D mesh (Apple Silicon) | :5050 |
| 🤖 **Tax AI Social** | AI social media content engine for tax/accounting firms | :5055 |
| 🎙️ **Whisper STT** | 100% local speech-to-text for Open WebUI | :9000 |
| 🧠 **AI Model Training Studio** | Fine-tune and train AI models on custom data. LoRA training, data processing, export to Ollama. | :8501 |

---

## 🏗️ Architecture

```
                    🦙 Ollama (localhost:11434)
                    mistral:7b · deepseek-coder:6.7b
                    Apple Silicon MPS · ~4-10GB RAM
                           │
        ┌──────────────────┼──────────────────────┐
        │                  │                      │
        ▼                  ▼                      ▼
  💬 Open WebUI      📈 Quant AI           📧 Mail AI
  :3000              :8000                 :5051
  + SearXNG          FastAPI+ChromaDB      IMAP + LLM
  :8080              vectorbt              Auto-triage

        │                  │                      │
        ▼                  ▼                      ▼
  🧊 TripoSR         🤖 Tax AI Social   🧠 AI Training
  :5053              :5055              :8501
  Image→3D           Instagram/         LoRA/Fine-tune
  OBJ/GLB            Facebook/TikTok    Ollama Export
  Apple Silicon      Compliance         Data Processing
```

---

## 📋 Requirements

- **macOS** (Apple Silicon M1/M2/M3/M4 recommended) or Linux
- **16 GB RAM** recommended (8GB minimum for basic use)
- **Docker Desktop** — https://www.docker.com/products/docker-desktop/
- **15+ GB free disk space** (for models + tools)
- Internet connection (for initial setup only)

---

## 🚀 Quick Start

### Step 1 — Clone the repo
```bash
git clone https://github.com/jup313/MYLLM.git
cd MYLLM
```

### Step 2 — Run setup
```bash
chmod +x setup.sh install-tools.sh
./setup.sh
```

This will:
- Install Ollama
- Download `mistral:7b` and `deepseek-coder:6.7b` models
- Start Open WebUI on http://localhost:3000
- Start SearXNG on http://localhost:8080

### Step 3 — Create your account
1. Open http://localhost:3000
2. Click **Sign Up** and create your admin account
3. The first account is automatically admin

---

## 💬 Tool 1 — Open WebUI + SearXNG

**Chat with local AI models + private web search.**

| URL | Description |
|-----|-------------|
| http://localhost:3000 | Chat interface |
| http://localhost:8080 | SearXNG search engine |

### Enable web search
1. Click the **✨ sparkle icon** in chat input
2. Toggle **Web Search** ON
3. Ask any question — AI searches privately via SearXNG

### Install Shopping Search Tool
```bash
./install-tools.sh your@email.com yourpassword
```

---

## 📈 Tool 2 — Quant AI

**AI-powered stock and crypto analysis running 100% locally.**

```bash
cd quant_api
pip install -r requirements.txt
python main.py
```

- FastAPI + ChromaDB vector database
- vectorbt for backtesting
- curl-cffi for market data
- Ask natural language questions about stocks and crypto

---

## 📧 Tool 3 — Mail AI Manager ⭐ UPDATED

**🎉 Now works with ANY IMAP email provider (Gmail, iCloud, Outlook, ProtonMail) — no Gmail API restrictions!**

Local AI that classifies, summarizes, categorizes, and drafts replies to your emails.

```bash
cd mail-ai-manager
python3 app.py
# Open: http://localhost:5051
```

### What's New in Phase 4 ✨

**Migration from Gmail Manager to universal Mail AI Manager:**
- ✅ **Works with any IMAP provider** — Gmail, iCloud, Outlook, ProtonMail, etc.
- ✅ **No OAuth complexity** — Just IMAP credentials (app-specific password)
- ✅ **100% local** — Zero cloud dependencies, zero API restrictions
- ✅ **Hybrid IMAP + AppleScript** — Reliable with native macOS Mail.app fallback
- ✅ **Feature parity** — All Gmail manager features ported to Mail system
- ✅ **Same AI classification** — Work, spam, personal, urgent categorization
- ✅ **Approval queue** — All actions require review before execution
- ✅ **Draft replies** — LLM-powered reply suggestions
- ✅ **Unsubscribe handling** — RFC 2369 compliant automatic unsubscribe

### Quick Start (5 Minutes)

```bash
cd mail-ai-manager
python3 app.py  # Start Flask server at http://localhost:5051

# In another terminal:
curl -X POST http://localhost:5051/api/mail/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "mail_imap_host": "imap.gmail.com",
    "mail_imap_port": "993",
    "mail_imap_username": "your-email@gmail.com",
    "mail_imap_password": "your-app-password",
    "mail_account_name": "Gmail"
  }'
```

### Supported Providers

| Provider | IMAP Host | Port | Notes |
|----------|-----------|------|-------|
| **Gmail** | `imap.gmail.com` | 993 | Requires 16-char app-specific password |
| **iCloud** | `imap.mail.me.com` | 993 | Requires app-specific password |
| **Outlook** | `outlook.office365.com` | 993 | Use main password or app password if 2FA |
| **ProtonMail** | `127.0.0.1` | 1143 | Via IMAP Bridge (localhost) |
| **Custom** | Any IMAP server | Any | Any IMAP-compatible email service |

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/status` | GET | Check system status (Ollama, mail connection) |
| `/api/mail/test-connection` | POST | Test IMAP credentials |
| `/api/mail/status` | GET | Check Mail connection status |
| `/api/setup` | POST | Save IMAP config |
| `/api/pipeline/run` | POST | Start email classification (max 30 emails) |
| `/api/pipeline/status` | GET | Check pipeline progress |
| `/api/emails` | GET | List classified emails |
| `/api/actions` | GET | List pending actions (archive, trash, flag) |
| `/api/actions/{id}/approve` | POST | Approve action |
| `/api/actions/{id}/reject` | POST | Reject action |

### Documentation

- **PHASE4_QUICKSTART.md** — 5-minute setup guide with curl examples
- **PHASE4_TEST_REPORT.md** — Full integration test results + troubleshooting
- **MAIL_AI_SETUP.md** — Provider-specific setup guides
- **MAIL_AI_MIGRATION_GUIDE.md** — Phase 3 migration details

### Architecture

```
Mail AI Manager (Phase 4)
├── mail_client.py
│   ├── IMAPMailClient (primary)
│   ├── AppleScriptMailClient (fallback)
│   └── HybridMailClient (orchestrator)
├── mail_action_engine.py
│   ├── fetch_unread_mail() — Get emails from INBOX
│   ├── run_pipeline() — Fetch → Classify → Route
│   ├── execute_action() — Archive, trash, flag, read
│   └── Approval queue system
├── app.py (Flask API)
├── database.py (SQLite)
└── llm_engine.py (Ollama integration)
```

### Configuration Example

```json
{
  "mail_imap_host": "imap.gmail.com",
  "mail_imap_port": "993",
  "mail_imap_username": "your-email@gmail.com",
  "mail_imap_password": "your-app-password",
  "mail_account_name": "Gmail",
  "ollama_model": "mistral",
  "auto_archive_spam": "true",
  "require_approval": "true",
  "auto_threshold": "0.90"
}
```

### Performance

- **IMAP connect:** ~500ms
- **Fetch 30 emails:** ~2-3s
- **Classify 30 emails:** ~10-30s (depends on LLM model)
- **Full pipeline (30 emails):** ~15-40s

### 🔐 Security

- ✅ Passwords stored locally in SQLite (no cloud)
- ✅ Use app-specific passwords (not main account password)
- ✅ 100% local processing — no data leaves your Mac
- ✅ Ollama runs locally — no API calls to external services

### Known Limitations

- IMAP-compatible provider required
- Unsubscribe requires `List-Unsubscribe` header in email
- AppleScript fallback limited to macOS Mail.app
- Local Ollama must be running separately

### Troubleshooting

**IMAP connection failed?**
```bash
python3 << 'EOF'
import imaplib
try:
    imap = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    imap.login('user@gmail.com', 'app-password')
    print("✅ Success!")
except Exception as e:
    print(f"❌ Error: {e}")
EOF
```

**Ollama not running?**
```bash
curl http://localhost:11434/api/tags  # Check status
ollama serve &                        # Start if needed
```

### Folder Name Update

The folder has been renamed from `gmail-ai-manager` to `mail-ai-manager` to better reflect its universal IMAP provider support. All functionality remains the same.

---

## 🧊 Tool 4 — TripoSR 3D Pipeline

**Generate 3D meshes from images using Apple Silicon GPU (MPS).**

```bash
cd triposr-pipeline
bash setup.sh     # First time only — installs TripoSR
bash start-ui.sh
# Open: http://localhost:5050
```

**Pipeline:**
```
Your prompt → Stable Diffusion image → TripoSR → OBJ/GLB mesh
```

- Uses Apple Silicon MPS (Metal Performance Shaders)
- Memory usage: ~6–10GB
- Output: OBJ + GLB files ready for Blender, Unity, web
- Best open-source 3D model for Mac 16GB

---

## 🤖 Tool 5 — Tax AI Social ⭐ NEW

**AI-powered social media content engine for tax preparation, tax resolution, and bookkeeping firms.**

### What it does
- Automatically generates **Instagram, Facebook, and TikTok** posts daily at 6 AM
- Uses your local Ollama LLM (`mistral:7b`) — no OpenAI API needed
- **35+ compliance rules** block misleading tax claims automatically
- Human review dashboard — Approve ✅, Edit ✏️, or Reject ❌ before posting
- Auto-posts to Facebook/Instagram via Meta Graph API on approval
- Business contact info (phone, WhatsApp, email, website) auto-appended to every post

### Setup
```bash
cd tax-ai-social
bash setup.sh
cp .env.example .env
# Edit .env — add your firm info and Meta API credentials
bash start.sh
# Open: http://localhost:5055
```

### Dashboard features
- **⚡ Generate Now** — single post or full daily batch (5 posts)
- **📋 Posts tab** — review drafts, approve, edit, or reject
- **⚙️ Business Settings tab** — update firm name, phone, email, website, WhatsApp, fax, etc. without touching files
- **6 AM auto-generation** — every morning, 5 posts ready for review
- **Compliance checker** — flags and blocks prohibited phrases before you see them

### Platforms supported
| Platform | Type | Auto-posts? |
|----------|------|-------------|
| Instagram | Image caption | ✅ (with image URL) |
| Facebook | Text post | ✅ |
| TikTok | Video script | ❌ Manual (record yourself) |

### Specialties supported
- Tax Preparation
- Tax Resolution (IRS debt, payment plans, OIC)
- Bookkeeping

---

## 🤖 AI Models

| Model | Size | Best For |
|-------|------|----------|
| `mistral:7b` | 4.4 GB | General chat, posts, email, social media |
| `deepseek-coder:6.7b` | 3.8 GB | Code generation, debugging, quant analysis |

### Pull additional models
```bash
ollama pull llama3.2        # Meta's Llama 3.2 (3B)
ollama pull phi4            # Microsoft Phi-4 (14B)
ollama pull qwen2.5-coder   # Qwen coding model
ollama list                 # See all installed models
```

---

## 🛑 Stop / Start Services

```bash
# Stop Docker services (Open WebUI + SearXNG)
docker compose down

# Start Docker services
docker compose up -d

# View logs
docker compose logs -f

# Restart a specific service
docker compose restart open-webui
```

---

## 📁 Project Structure

```
MYLLM/
├── README.md                     # This file
├── docker-compose.yml            # Open WebUI + SearXNG
├── setup.sh                      # One-command setup
├── install-tools.sh              # Install Open WebUI tools
├── shopping_search_tool.py       # Amazon/eBay search tool
├── quant_tool.py                 # Quant analysis Open WebUI tool
├── searxng/                      # SearXNG config
├── quant_api/                    # Quant AI FastAPI backend
├── mail-ai-manager/              # Mail AI email manager (IMAP)
├── triposr-pipeline/             # Image → 3D mesh pipeline
│   ├── architecture.svg          # Full stack diagram
│   └── ...
├── tax-ai-social/                # ⭐ Tax AI Social Media Engine
│   ├── app/
│   │   ├── main.py               # Flask API + routes
│   │   ├── generator.py          # Post generation engine
│   │   ├── compliance.py         # 35+ tax compliance rules
│   │   ├── poster.py             # Meta Graph API posting
│   │   ├── scheduler.py          # 6 AM daily auto-generation
│   │   └── database.py           # SQLite post tracking
│   ├── prompts/                  # 7 platform-specific prompts
│   ├── templates/index.html      # Dark-mode dashboard
│   ├── .env.example              # Config template
│   ├── requirements.txt
│   ├── setup.sh
│   └── start.sh
└── whisper-stt/                  # ⭐ Local Voice / Speech-to-Text
    ├── server.py                 # OpenAI-compatible STT API
    ├── requirements.txt
    ├── setup.sh
    ├── start.sh
    └── README.md
```

---

## 🔧 Troubleshooting

### Ollama not connecting
```bash
ollama list          # Check if running
ollama serve         # Start if not running
```

### Docker containers not starting
```bash
docker compose down
docker compose up -d
docker compose logs
```

### Tax AI Social — Ollama model not found
```bash
ollama pull mistral:7b     # Download the model
ollama serve               # Make sure Ollama is running
```

### Port conflicts
Edit `docker-compose.yml` or the relevant `.env` file to change ports.

---

## 🔒 Privacy

Everything runs **100% locally**:
- No data sent to OpenAI, Anthropic, or any cloud service
- SearXNG proxies web searches anonymously
- Gmail AI only reads emails locally via OAuth — nothing uploaded
- Tax AI Social posts never leave until you click Approve
- All AI inference runs on your Mac's Apple Silicon chip

---

## 🎙️ Tool 6 — Whisper STT ⭐ NEW

**100% local speech-to-text for Open WebUI — talk to your AI instead of typing.**

```bash
cd whisper-stt
bash start.sh
# Server starts at http://localhost:9000
```

First run downloads the Whisper `small` model (~460 MB, one time).

### Connect to Open WebUI
1. Open **http://localhost:3000**
2. Profile icon → **Settings** → **Audio**
3. Speech to Text:
   - Engine: **OpenAI API**
   - Base URL: `http://localhost:9000/v1`
   - API Key: `local`
4. Save — click the **🎤 microphone** in chat to speak!

### Model options
| Model | Size | Speed | Best For |
|-------|------|-------|----------|
| `tiny` | ~75 MB | ~0.3s | Quick testing |
| `base` | ~145 MB | ~0.5s | English-only |
| `small` | ~460 MB | ~1s | **Recommended ✅** |
| `medium` | ~1.5 GB | ~3s | Best accuracy |

```bash
WHISPER_MODEL=medium bash start.sh   # Use a larger model
```

- ✅ 100% private — audio never leaves your Mac
- ✅ Works offline after first setup
- ✅ Multi-language support (auto-detects)
- ✅ OpenAI-compatible API format

---

## 📈 Quant AI — Portfolio Tracker Dashboard

**Track your stock/crypto holdings with live prices, gain/loss, and allocation chart.**

Open: **http://localhost:8000/portfolio**

| Feature | Details |
|---------|---------|
| 📊 Positions table | Ticker, shares, avg cost, current price, gain/loss, day change |
| 🍩 Allocation donut chart | Visual portfolio breakdown (Chart.js) |
| 👁️ Watchlist | Track tickers without holding them |
| ⟳ Live prices | Auto-fetches via Yahoo Finance on page load |
| ➕ Add / remove | Simple form — no file editing needed |

```bash
cd quant_api
python main.py
# Open: http://localhost:8000/portfolio
```

---

## 📅 Gmail AI — Calendar Integration

**Detect meetings in emails and add them to Google Calendar automatically.**

Open: **http://localhost:5051** → click **📅 Calendar** in sidebar

| Feature | Details |
|---------|---------|
| 🔍 Meeting detection | Scans emails for Zoom, time mentions, meeting keywords |
| 🤖 LLM extraction | Uses Ollama to extract date/time/location from email body |
| 📅 One-click add | Click **📅 Add to Calendar** on any detected meeting email |
| ➕ Manual events | Create events directly from the dashboard |
| 📋 Upcoming view | See next 7 days of Google Calendar events |

**Requires:** Google Calendar API scope (enabled automatically when you re-connect Gmail OAuth)

> ⚠️ If you already connected Gmail, click **🔗 Re-connect Gmail** in Settings to add Calendar scope.

---

## 🎨 Tool 7 — Stable Diffusion Image Generation

**100% local text-to-image generation on your Mac. No API key. No cloud. No limits.**

```bash
cd stable-diffusion
bash setup.sh     # First time only (~2-3 min)
bash start.sh
# Open: http://localhost:5050
```

| Feature | Details |
|---------|---------|
| ⚡ SDXL-Turbo | Default model — ~3–8s per image on M1/M2/M3 |
| 🧠 6 Models | SDXL-Turbo, SD 2.1, SD 1.5, DreamShaper, OpenJourney, Realistic Vision |
| 📐 Any size | 512×512 to 1280×1280 with 1:1, 16:9, 9:16, 4:3 presets |
| 🎲 Seed control | Reproduce or vary any image |
| 🗂️ History | Browse all generated images |
| 📱 Social Post tab | Auto-generate images for Tax AI Social posts |

### Tax AI Social Integration

When Stable Diffusion is running (`:5050`), Tax AI Social will **automatically generate images** for Instagram and Facebook posts. Just start both services:

```bash
# Terminal 1
cd stable-diffusion && bash start.sh

# Terminal 2
cd tax-ai-social && bash start.sh
```

Images are auto-selected based on post content (IRS/debt → resolution style, family → family style, etc.).

### API

```bash
# Generate image
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "professional tax accountant, modern office, 4K", "model": "sdxl-turbo", "steps": 4}'

# Use in Python
from stable_diffusion.sd_client import generate_for_post
img_url = generate_for_post("Tax deadline April 15th", specialty="tax_preparation")
```

---

## 🗺️ Roadmap

- [x] ~~Stable Diffusion image generation~~ — ✅ Done! (`stable-diffusion/` + Tax AI Social integration)
- [ ] LinkedIn support for Tax AI Social
- [x] ~~Quant AI portfolio tracker dashboard~~ — ✅ Done! (`/portfolio`)
- [x] ~~Gmail AI calendar integration~~ — ✅ Done! (Calendar tab)
- [x] ~~Voice interface for Open WebUI~~ — ✅ Done! (Whisper STT)

---

## 🧠 Tool 8 — AI Model Training Studio ⭐ NEW

**Fine-tune and train AI models on your custom data. LoRA training, data processing, export to Ollama. Built with Streamlit.**

```bash
cd ai-model-training
streamlit run app.py
# Open: http://localhost:8501
```

### What it does
- **📄 Data import** — Load training data from PDF, TXT, or CSV files
- **🎓 LoRA training** — Fine-tune models without retraining from scratch
- **🧠 Model selection** — Train on any Ollama model (mistral:7b, llama2, etc.)
- **📊 Training dashboard** — Monitor loss, accuracy, training progress in real-time
- **💾 Export to Ollama** — Save trained models as Ollama-compatible formats
- **⚙️ Hyperparameter tuning** — Control learning rate, batch size, epochs, etc.
- **✅ Data validation** — Automatic data cleaning and quality checks

### Quick Start

```bash
cd ai-model-training
pip install -r requirements.txt
streamlit run app.py
# Open: http://localhost:8501
```

### Features
| Feature | Details |
|---------|---------|
| 📚 Multi-format input | PDF, TXT, JSON, CSV training data |
| 🎯 LoRA training | Low-rank adaptation — fast fine-tuning |
| 🧠 Model selection | Any Ollama model supported |
| 📈 Real-time monitoring | Loss curves, accuracy tracking |
| 💾 Export formats | GGUF, SafeTensors, PyTorch |
| 🚀 One-click deploy | Export directly to Ollama |
| 📊 Data processing | Auto-tokenization, chunking, filtering |

### Training workflow
```
Your Data (PDF/TXT) → Data Processing → LoRA Training → Model Export → Ollama
```

### Use cases
- **Specialized domain knowledge** — Train on your company docs, legal contracts, industry papers
- **Custom business logic** — Fine-tune to your specific use cases (tax terms, medical jargon, code style)
- **Faster inference** — Create smaller, specialized models for specific tasks
- **Privacy-first** — All training happens locally on your Mac

---

Built with ❤️ using [Ollama](https://ollama.com) · [Open WebUI](https://github.com/open-webui/open-webui) · [SearXNG](https://github.com/searxng/searxng) · [TripoSR](https://github.com/VAST-AI-Research/TripoSR) · [Streamlit](https://streamlit.io) · [Flask](https://flask.palletsprojects.com) · Apple Silicon 🍎
