# 🤖 MyLLM – Personal AI Stack on Your Mac

Run a complete private AI ecosystem locally using **Ollama**, **Open WebUI**, and purpose-built tools for email, finance, 3D generation, and social media marketing. No cloud. No subscriptions. No data leaving your machine.

![Architecture](triposr-pipeline/architecture.svg)

---

## 🧰 Tools in This Stack

| Tool | Purpose | Port |
|------|---------|------|
| 💬 **Open WebUI + SearXNG** | Chat UI with private web search | :3000 / :8080 |
| 📈 **Quant AI** | Stock & crypto analysis with local LLM | :8000 |
| 📬 **Gmail AI Manager** | AI email triage, summarize, draft replies | :5051 |
| 🧊 **TripoSR 3D Pipeline** | Image → 3D mesh (Apple Silicon) | :5050 |
| 🤖 **Tax AI Social** ⭐ NEW | AI social media content engine for tax/accounting firms | :5055 |

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
  💬 Open WebUI      📈 Quant AI           📬 Gmail AI
  :3000              :8000                 :5051
  + SearXNG          FastAPI+ChromaDB      Gmail API
  :8080              vectorbt              Auto-triage

        │                  │
        ▼                  ▼
  🧊 TripoSR         🤖 Tax AI Social
  :5050              :5055
  Image→3D           Instagram/Facebook/TikTok
  OBJ/GLB export     Compliance + Auto-Post
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

## 📬 Tool 3 — Gmail AI Manager

**Local AI that reads, summarizes, categorizes, and drafts replies to your emails.**

```bash
cd gmail-ai-manager
bash setup.sh
bash start.sh
# Open: http://localhost:5051
```

Features:
- ✅ Auto-summarize inbox (no email ever leaves your machine)
- ✅ Categorize by priority (urgent / action / info / promo)
- ✅ Draft AI replies with one click
- ✅ Unsubscribe detection
- ✅ Requires Gmail OAuth credentials (stays 100% local)

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
├── gmail-ai-manager/             # Gmail AI email manager
├── triposr-pipeline/             # Image → 3D mesh pipeline
│   ├── architecture.svg          # Full stack diagram
│   └── ...
└── tax-ai-social/                # ⭐ Tax AI Social Media Engine
    ├── app/
    │   ├── main.py               # Flask API + routes
    │   ├── generator.py          # Post generation engine
    │   ├── compliance.py         # 35+ tax compliance rules
    │   ├── poster.py             # Meta Graph API posting
    │   ├── scheduler.py          # 6 AM daily auto-generation
    │   └── database.py           # SQLite post tracking
    ├── prompts/                  # 7 platform-specific prompts
    ├── templates/index.html      # Dark-mode dashboard
    ├── .env.example              # Config template
    ├── requirements.txt
    ├── setup.sh
    └── start.sh
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

## 🗺️ Roadmap

- [ ] Stable Diffusion image generation for social posts
- [ ] LinkedIn support for Tax AI Social
- [ ] Quant AI portfolio tracker dashboard
- [ ] Gmail AI calendar integration
- [ ] Voice interface for Open WebUI

---

Built with ❤️ using [Ollama](https://ollama.com) · [Open WebUI](https://github.com/open-webui/open-webui) · [SearXNG](https://github.com/searxng/searxng) · [TripoSR](https://github.com/VAST-AI-Research/TripoSR) · [Flask](https://flask.palletsprojects.com) · Apple Silicon 🍎
