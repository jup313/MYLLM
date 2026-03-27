# 📧 Mail AI Manager — macOS Mail Integration

**Local LLM-powered Mail management — runs 100% on your Mac with zero Gmail API restrictions.**

Manages any IMAP-based email account (Gmail, iCloud, Outlook, ProtonMail, etc.) using hybrid IMAP + AppleScript architecture.

---

## ✨ Features (Full Parity with Gmail Manager)

| Feature | Status | Notes |
|---------|--------|-------|
| 🧠 **Local LLM Classification** | ✅ | Classifies: urgent/work/personal/marketing/spam/notification |
| ✅ **Approval Queue** | ✅ | All AI actions require your approval |
| ✍️ **Draft Reply Generator** | ✅ | AI drafts replies you can edit |
| 🗑️ **Smart Spam Detection** | ✅ | Auto-trash high-confidence spam |
| 🚫 **Safe Unsubscribe** | ✅ | RFC 2369 headers only |
| 📊 **Daily/Weekly Summaries** | ✅ | HTML digest reports |
| 📋 **Audit Log** | ✅ | All actions timestamped |
| 🔒 **100% Private** | ✅ | No cloud, no OAuth restrictions |
| 🍎 **macOS Native** | ✅ | IMAP primary + AppleScript fallback |

---

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Ensure Python 3.11+
python3 --version

# Install dependencies
pip3 install -r requirements.txt

# Ollama must be running
ollama serve &
```

### 2. Configure Mail Account

Create `mail_config.json` in the `mail-ai-manager` folder:

```json
{
  "mail_imap_host": "imap.gmail.com",
  "mail_imap_port": 993,
  "mail_imap_username": "your-email@gmail.com",
  "mail_imap_password": "your-app-password",
  "mail_account_name": "My Gmail Account"
}
```

**For Different Providers:**

| Provider | IMAP Host | Port |
|----------|-----------|------|
| Gmail | `imap.gmail.com` | 993 |
| iCloud | `imap.mail.me.com` | 993 |
| Outlook | `outlook.office365.com` | 993 |
| ProtonMail | `127.0.0.1` (Bridge only) | 1143 |

### 3. Generate App-Specific Password

**Gmail:**
1. Go to [Google Account Settings](https://myaccount.google.com)
2. Security → 2-Step Verification
3. App passwords → Select Mail and macOS
4. Copy the generated password (use this in config)

**iCloud:**
1. [Apple ID](https://appleid.apple.com) → Security
2. App-Specific Passwords → Generate
3. Copy password

### 4. Start the Service

```bash
cd mail-ai-manager
bash setup.sh      # Install dependencies
bash start.sh      # Start server

# Opens http://localhost:5051 automatically
```

### 5. Configure in Web UI

1. **Step 1 — Mail Account**: Test IMAP connection
2. **Step 2 — LLM**: Select Ollama model
3. **Step 3 — Behavior**: Set automation preferences
4. **Step 4 — Review**: Verify configuration

---

## 🏗️ Architecture

```
mail-ai-manager/
├── mail_client.py          # NEW: IMAP + AppleScript hybrid
├── mail_action_engine.py   # NEW: Mail-specific actions
├── app.py                  # Flask web server (adapted)
├── database.py             # SQLite (config updated)
├── llm_engine.py           # LLM classification (unchanged)
├── summarizer.py           # Summary generation (unchanged)
├── unsubscribe.py          # RFC 2369 unsubscribe (unchanged)
├── index.html              # Web UI (adapted for Mail)
├── setup.sh                # Setup script
├── start.sh                # Start script
└── mail_ai.db              # SQLite database (auto-created)
```

### Pipeline Flow

```
Any IMAP Email Account
    ↓
fetch_unread_mail() [IMAP]
    ↓
classify_email() [LLM]
    ↓
Action Router:
    • High confidence spam → auto-trash
    • Requires approval → queue
    • Draft needed → generate
    ↓
execute_action() [IMAP/AppleScript]
    • Archive (IMAP MOVE)
    • Trash (IMAP DELETE)
    • Flag/Read (IMAP FLAGS or AppleScript)
    • Unsubscribe (RFC 2369)
    ↓
Audit Log + Summary
```

---

## ⚙️ Configuration

All settings are saved in the web UI. Key options:

| Setting | Default | Description |
|---------|---------|-------------|
| `auto_archive_spam` | `true` | Auto-trash spam ≥90% confidence |
| `auto_unsubscribe` | `false` | Auto-unsubscribe marketing |
| `require_approval` | `true` | Queue all actions for review |
| `auto_threshold` | `0.90` | Min confidence for auto-actions |
| `rate_limit_per_run` | `10` | Max auto-actions per pipeline run |

---

## 🔧 Hybrid IMAP + AppleScript Architecture

### Why Hybrid?

**IMAP (Primary):**
- ✅ Works with any IMAP provider
- ✅ Stable and reliable
- ✅ No Mail.app dependency
- ❌ Limited to IMAP protocol features

**AppleScript (Fallback):**
- ✅ Native Mail.app integration
- ✅ Access to Mail-specific features
- ✅ Fallback if IMAP fails
- ❌ Requires Mail.app running
- ❌ Slower than IMAP

### How It Works

```python
# mail_client.py uses this strategy:

try:
    # Primary: Use IMAP
    imap_client.connect()
    result = imap_client.mark_read(email_id)
except:
    # Fallback: Use AppleScript
    if applescript_available:
        result = applescript_client.mark_read_applescript(email_id)
```

### Mail-Specific Operations

| Operation | Method | Fallback |
|-----------|--------|----------|
| Fetch emails | IMAP FETCH | Not available |
| Mark read | IMAP FLAGS | AppleScript |
| Flag email | IMAP FLAGS | AppleScript |
| Move to folder | IMAP MOVE | AppleScript |
| Delete | IMAP DELETE | AppleScript |
| Get accounts | - | AppleScript |

---

## 🔒 Privacy & Safety

- ✅ **All data stays local** — IMAP to local SQLite only
- ✅ **No cloud** — Zero internet requests except to your mail server
- ✅ **Credentials encrypted** — Stored in SQLite (consider full-disk encryption)
- ✅ **No body link clicking** — Unsubscribe uses RFC 2369 headers only
- ✅ **Approval required** — All sensitive actions need your confirmation

---

## 🛠️ Troubleshooting

### IMAP Connection Fails

```bash
# Test IMAP manually
python3 -c "
import imaplib
imap = imaplib.IMAP4_SSL('imap.gmail.com', 993)
imap.login('your-email@gmail.com', 'app-password')
print('✅ IMAP works!')
"
```

**Common Issues:**
- Wrong password → Use app-specific password, not regular password
- 2FA enabled → Gmail requires app-specific passwords
- Port blocked → Use 993 (SSL), not 143
- IMAP disabled → Enable in mail provider settings

### AppleScript Fallback Not Working

```bash
# Check if osascript is available
which osascript
osascript -e 'tell app "Mail" to activate'
```

**Requirements:**
- macOS 10.14+
- Mail.app running
- Full Disk Access granted to Terminal (Settings → Privacy)

### Emails Not Fetching

1. Verify IMAP credentials in web UI
2. Check unread count in Mail.app
3. Verify mailbox name (usually "INBOX")
4. Check logs: `tail -f mail_ai.db.log`

### LLM Not Working

```bash
# Verify Ollama
curl http://localhost:11434/api/tags
ollama list
```

Ensure model is loaded:
```bash
ollama pull mistral:7b
```

---

## 📊 Monitoring

### Check Database

```bash
# View configuration
sqlite3 mail_ai.db "SELECT * FROM config;"

# View processed emails
sqlite3 mail_ai.db "SELECT id, subject, category, confidence FROM emails LIMIT 10;"

# View pending actions
sqlite3 mail_ai.db "SELECT * FROM actions WHERE status='pending';"
```

### View Logs

```bash
# Flask logs (web server)
tail -f /tmp/mail_ai_manager.log

# Application logs (see console output)
# Check terminal where mail_ai_manager is running
```

---

## 🚀 Advanced Usage

### Multiple Mail Accounts

Currently supports one primary account. To add multiple:

1. Run separate instances on different ports
2. Or modify `mail_client.py` to support account switching

### Custom LLM Models

In web UI → Settings:
- Switch to any Ollama model
- Test connection
- Pipeline will use new model

### Scheduling Runs

```bash
# Run pipeline every 5 minutes via cron
*/5 * * * * curl -X POST http://localhost:5051/api/pipeline/run -H "Content-Type: application/json" -d '{"max_emails": 20}'
```

---

## 📝 License

MIT — free to use, modify, and distribute.

---

## 🤝 Migration from Gmail Manager

If you're upgrading from `gmail-ai-manager`:

1. **Database:** Old data stays in old db file; new system uses fresh database
2. **Configuration:** Manually enter IMAP credentials instead of OAuth
3. **Features:** All features maintained (classification, drafts, summaries, etc.)
4. **Benefit:** No Gmail API restrictions, works with any IMAP provider

---

## 📧 Support

For issues or questions:
1. Check logs in the web UI (API logs tab)
2. Test IMAP connection manually
3. Verify Ollama is running
4. Review database for processing errors

---

**Built with:** Flask · IMAP · AppleScript · Ollama · SQLite · 100% Local
