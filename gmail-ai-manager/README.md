# 📬 Gmail AI Manager

**Local LLM-powered Gmail management — runs 100% on your Mac. No cloud AI. No data leaves your machine.**

Built for **Mac 16GB** (M1/M2/M3/M4) using Ollama + Mistral/LLaMA3.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Local LLM Classification** | Classifies every email: urgent / work / personal / marketing / spam / notification |
| ✅ **Approval Queue** | All AI actions require your approval before executing |
| ✍️ **Draft Reply Generator** | AI drafts replies you can edit + send or save to Gmail |
| 🗑️ **Smart Spam Trash** | Auto-trash high-confidence spam (configurable threshold) |
| 🚫 **Safe Unsubscribe** | RFC 2369 List-Unsubscribe only — never clicks body links |
| 📊 **Daily/Weekly Summaries** | Beautiful HTML digest reports of your inbox |
| 📋 **Audit Log** | Every action logged with timestamp + result |
| 🔐 **OAuth2 Gmail** | Google OAuth2 — token stored locally only |

---

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11+
brew install python@3.11

# Install Ollama
brew install ollama

# Pull a model (mistral:7b recommended for 16GB Mac)
ollama pull mistral:7b

# Start Ollama
ollama serve
```

### 2. Setup

```bash
cd gmail-ai-manager
bash setup.sh
```

### 3. Start

```bash
bash start.sh
# Opens http://localhost:5051 automatically
```

### 4. Configure in the UI

1. **Step 1 — Google API**: Enter your OAuth2 credentials ([how to get them](#google-api-setup))
2. **Step 2 — LLM**: Point to Ollama, choose your model, test connection
3. **Step 3 — Behavior**: Set automation preferences
4. **Step 4 — Connect Gmail**: OAuth2 sign-in

---

## 🔑 Google API Setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. **APIs & Services** → **Library** → enable **Gmail API**
4. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
   - Application type: **Desktop app**
5. Copy the **Client ID** and **Client Secret** into the Setup Wizard
6. Add `http://localhost:5051` to **Authorized redirect URIs**

> ✅ All credentials are stored locally in SQLite — nothing is sent to any remote server.

---

## 🧠 Recommended Models (16GB Mac)

| Model | Size | Best for |
|-------|------|----------|
| `mistral:7b` | ~4GB | Best overall for email classification |
| `llama3:8b` | ~5GB | Good quality, slightly slower |
| `deepseek-coder:6.7b` | ~4GB | Good for technical emails |
| `gemma:7b` | ~5GB | Alternative option |

```bash
ollama pull mistral:7b   # recommended
```

---

## 🏗️ Architecture

```
gmail-ai-manager/
├── app.py              # Flask web server + API routes
├── database.py         # SQLite storage (emails, actions, logs, config)
├── gmail_client.py     # Gmail API + OAuth2 client
├── llm_engine.py       # Ollama LLM classify/draft/summarize
├── action_engine.py    # Pipeline orchestrator + action executor
├── unsubscribe.py      # Safe RFC 2369 unsubscribe handler
├── summarizer.py       # Daily/weekly HTML summary generator
├── index.html          # Full web dashboard (no npm/node needed)
├── setup.sh            # One-command dependency installer
├── start.sh            # Start server + open browser
└── gmail_ai.db         # SQLite database (auto-created, gitignored)
```

### Pipeline Flow

```
Gmail API → Fetch emails
    ↓
LLM Engine → Classify (category + confidence + suggested action)
    ↓
Action Engine → Auto-act (spam trash) or Queue for approval
    ↓
Approval Queue (UI) → You approve/reject each action
    ↓
Execute: archive / label / draft reply / send / unsubscribe
```

---

## ⚙️ Configuration

All settings are in the web UI → **Settings** tab. Key options:

| Setting | Default | Description |
|---------|---------|-------------|
| `auto_archive_spam` | `true` | Auto-trash spam ≥90% confidence |
| `auto_unsubscribe` | `false` | Auto-unsubscribe marketing (RFC headers only) |
| `require_approval` | `true` | Queue all actions for manual review |
| `auto_threshold` | `0.90` | Minimum confidence for auto-actions |
| `rate_limit_per_run` | `10` | Max auto-actions per pipeline run |

---

## 🔒 Privacy & Safety

- **All data stays local** — SQLite + local Ollama
- **OAuth2 token** stored only in `token.json` (gitignored)
- **No body link clicking** — unsubscribe uses RFC 2369 headers only
- **Approval required** for send/unsubscribe by default
- **SSL verification** enforced for all HTTP requests

---

## 📝 License

MIT — free to use, modify, and distribute.
