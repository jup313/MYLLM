# 📬 Mail AI Manager

**Local LLM-powered email management — runs 100% on your Mac. No cloud AI. No data leaves your machine.**

Built for **Mac 16GB** (M1/M2/M3/M4) using Ollama + Mistral/LLaMA3.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Local LLM Classification** | Classifies every email: urgent / work / personal / marketing / spam / notification |
| ✅ **Approval Queue** | All AI actions require your approval before executing |
| ✍️ **Draft Reply Generator** | AI drafts replies you can edit + send or save |
| 🗑️ **Smart Spam Trash** | Auto-trash high-confidence spam (configurable threshold) |
| 🚫 **Safe Unsubscribe** | RFC 2369 List-Unsubscribe only — never clicks body links |
| 📊 **Daily/Weekly Summaries** | Beautiful HTML digest reports of your inbox |
| 📅 **Google Calendar Integration** | CalDAV-based calendar — view events and create new ones from AI suggestions |
| 📋 **Audit Log** | Every action logged with timestamp + result |
| 🔐 **IMAP + App Password** | Secure Gmail access via IMAP — uses Google App Password (no OAuth needed) |
| 👥 **Multi-Account Support** | Manage multiple Gmail accounts from one dashboard |

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

### 2. Install Dependencies

```bash
cd mail-ai-manager
pip install flask caldav imapclient beautifulsoup4 requests
```

### 3. Start

```bash
python app.py
# Opens http://localhost:5051
```

### 4. Configure in the UI

1. **Add Account** — Enter your Gmail address and App Password ([how to get one](#-how-to-get-a-google-app-password))
2. **LLM Settings** — Point to Ollama, choose your model, test connection
3. **Behavior** — Set automation preferences (auto-archive spam, approval queue, etc.)

---

## 🔑 Accounts & Passwords Setup

Mail AI Manager uses **IMAP** to read your email and **CalDAV** to access your Google Calendar. Both use the same **Google App Password** — no OAuth2 or Google Cloud Console setup required.

### What You Need

| Item | Description |
|------|-------------|
| **Gmail Address** | Your full Gmail address (e.g., `yourname@gmail.com`) |
| **Google App Password** | A 16-character password generated from your Google Account |

> ⚠️ **Important:** App Passwords require **2-Step Verification** to be enabled on your Google Account.

### The Same App Password Powers Everything

Once you generate a Google App Password, it is used for:

- 📧 **IMAP Email Access** — Fetching and managing your emails
- 📅 **CalDAV Calendar** — Reading and creating Google Calendar events

You only need **one App Password per Gmail account**.

---

## 🔐 How to Get a Google App Password

Follow these steps to generate an App Password for your Gmail account:

### Step 1: Enable 2-Step Verification

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Sign in with your Google account
3. Scroll down to **"How you sign in to Google"**
4. Click **2-Step Verification**
5. Follow the prompts to enable it (you'll need your phone for verification)

### Step 2: Generate an App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - If this link doesn't work, go to **Google Account** → **Security** → **2-Step Verification** → scroll to bottom → **App passwords**
2. You may need to sign in again
3. In the **"App name"** field, type a name like `Mail AI Manager`
4. Click **Create**
5. Google will display a **16-character password** (formatted like `abcd efgh ijkl mnop`)
6. **Copy this password** — you will need it in the next step

> ⚠️ **Save this password somewhere safe!** Google will only show it once. If you lose it, you'll need to generate a new one.

### Step 3: Add the Account in Mail AI Manager

1. Open Mail AI Manager at `http://localhost:5051`
2. Go to the **Settings** or **Accounts** section
3. Click **Add Account**
4. Enter:
   - **Email**: `yourname@gmail.com`
   - **Password**: The 16-character App Password from Step 2 (spaces are optional)
5. Click **Save** — the app will test the IMAP connection automatically

> ✅ All credentials are stored locally in SQLite (`gmail_ai.db`) — nothing is sent to any remote server.

---

## 📅 Google Calendar (CalDAV) Setup

Calendar integration works automatically once your account is configured. **No additional setup is required** — it uses the same Gmail address and App Password.

### How It Works

- Mail AI Manager connects to Google Calendar using the **CalDAV protocol**
- CalDAV URL: `https://www.google.com/calendar/dav/{your-email}/events/`
- Authentication uses your Gmail address + the same App Password
- You can view upcoming events and create new calendar entries from AI-suggested actions

### Calendar Features

| Feature | Description |
|---------|-------------|
| 📋 **View Events** | See your upcoming Google Calendar events in the dashboard |
| ➕ **Create Events** | AI can suggest calendar events from email content |
| 🔗 **Same Credentials** | Uses the same App Password as email — no extra setup |

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
mail-ai-manager/
├── app.py              # Flask web server + API routes (port 5051)
├── database.py         # SQLite storage (emails, actions, logs, config, accounts)
├── imap_client.py      # IMAP email client + HTML-to-text processing
├── calendar_engine.py  # CalDAV Google Calendar integration
├── llm_engine.py       # Ollama LLM classify/draft/summarize
├── action_engine.py    # Pipeline orchestrator + action executor
├── macos_mail.py       # macOS Mail.app integration utilities
├── index.html          # Full web dashboard (single-page, no npm/node needed)
└── gmail_ai.db         # SQLite database (auto-created, gitignored)
```

### Pipeline Flow

```
IMAP → Fetch emails (Gmail App Password)
    ↓
LLM Engine → Classify (category + confidence + suggested action)
    ↓
Action Engine → Auto-act (spam trash) or Queue for approval
    ↓
Approval Queue (UI) → You approve/reject each action
    ↓
Execute: archive / label / draft reply / send / unsubscribe
    ↓
Calendar Engine → Create events from email context (CalDAV)
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

- **All data stays local** — SQLite database + local Ollama LLM
- **App Password** stored only in local SQLite (gitignored database)
- **No OAuth2 / No Google Cloud Console** needed — just a simple App Password
- **No body link clicking** — unsubscribe uses RFC 2369 headers only
- **Approval required** for send/unsubscribe by default
- **IMAP over SSL** (port 993) for secure email access
- **CalDAV over HTTPS** for secure calendar access

---

## 🛠️ Troubleshooting

### "IMAP connection failed"
- Verify your App Password is correct (16 characters, no spaces needed)
- Make sure **IMAP is enabled** in Gmail: Go to Gmail → Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP
- Check that **2-Step Verification** is enabled on your Google Account

### "Calendar not connecting"
- Calendar uses the same App Password as email — no separate setup needed
- Verify the account is working for email first
- Check that Google Calendar is accessible at [calendar.google.com](https://calendar.google.com)

### "App Password option not showing"
- You **must** enable 2-Step Verification first
- Go to [myaccount.google.com/security](https://myaccount.google.com/security) → 2-Step Verification → turn it on
- Then visit [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

### "Ollama not responding"
- Make sure Ollama is running: `ollama serve`
- Verify a model is installed: `ollama list`
- Pull a model if needed: `ollama pull mistral:7b`

---

## 📝 License

MIT — free to use, modify, and distribute.
