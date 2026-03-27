# 🚀 Mail AI Manager — Phase 4 Quick Start Guide

## 📌 What Is This?

You now have a complete **Mail AI Manager** that:
- ✅ Works with ANY IMAP email provider (Gmail, iCloud, Outlook, ProtonMail, etc.)
- ✅ Uses AI to classify emails (work, spam, personal, etc.)
- ✅ Automatically archives spam or routes emails to appropriate folders
- ✅ Runs **100% locally** — no cloud API, no Gmail restrictions
- ✅ Uses **macOS Mail.app** or any email client supporting IMAP

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Start the Flask Server

```bash
cd /Volumes/EXTERNAL/MYLLM/gmail-ai-manager
python3 app.py
```

You should see:
```
╔══════════════════════════════════════════════════╗
║   📧 Mail AI Manager                           ║
║   Open: http://localhost:5051                  ║
╚══════════════════════════════════════════════════╝
```

**Leave this terminal open.** The server is now running.

---

### Step 2: Test IMAP Connection

Open a new terminal and test your email provider:

#### For Gmail:
```bash
curl -X POST http://localhost:5051/api/mail/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "mail_imap_host": "imap.gmail.com",
    "mail_imap_port": "993",
    "mail_imap_username": "your-email@gmail.com",
    "mail_imap_password": "your-16-char-app-password",
    "mail_account_name": "Gmail"
  }'
```

#### For iCloud:
```bash
curl -X POST http://localhost:5051/api/mail/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "mail_imap_host": "imap.mail.me.com",
    "mail_imap_port": "993",
    "mail_imap_username": "your-email@icloud.com",
    "mail_imap_password": "your-app-specific-password",
    "mail_account_name": "iCloud"
  }'
```

#### For Outlook:
```bash
curl -X POST http://localhost:5051/api/mail/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "mail_imap_host": "outlook.office365.com",
    "mail_imap_port": "993",
    "mail_imap_username": "your-email@outlook.com",
    "mail_imap_password": "your-password",
    "mail_account_name": "Outlook"
  }'
```

**Expected response if successful:**
```json
{
  "success": true,
  "message": "Connection successful",
  "mailboxes": ["INBOX", "[Gmail]/All Mail", "[Gmail]/Sent Mail", ...]
}
```

If you get an error, see **Troubleshooting** section below.

---

### Step 3: Save Configuration

Once connection test passes, save your configuration:

```bash
curl -X POST http://localhost:5051/api/setup \
  -H "Content-Type: application/json" \
  -d '{
    "mail_imap_host": "imap.gmail.com",
    "mail_imap_port": "993",
    "mail_imap_username": "your-email@gmail.com",
    "mail_imap_password": "your-16-char-app-password",
    "mail_account_name": "Gmail",
    "ollama_model": "mistral",
    "ollama_url": "http://localhost:11434",
    "auto_archive_spam": "true",
    "auto_unsubscribe": "false",
    "require_approval": "true",
    "auto_threshold": "0.90"
  }'
```

**Expected response:**
```json
{
  "success": true,
  "message": "Configuration saved"
}
```

---

### Step 4: Run the Pipeline

Now classify and process your emails:

```bash
curl -X POST http://localhost:5051/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"max_emails": 10}'
```

This will:
1. Fetch 10 unread emails from your INBOX
2. Classify each one using AI
3. Queue spam for auto-archiving
4. Show other emails for your review

**Check status:**
```bash
curl http://localhost:5051/api/pipeline/status | jq
```

---

### Step 5: View Results

**See classified emails:**
```bash
curl http://localhost:5051/api/emails | jq
```

**See pending actions (awaiting your approval):**
```bash
curl http://localhost:5051/api/actions | jq
```

**Approve an action:**
```bash
curl -X POST http://localhost:5051/api/actions/1/approve \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 🔑 Important: Getting IMAP Passwords

### Gmail
1. Enable 2-factor authentication
2. Go to https://myaccount.google.com/apppasswords
3. Select "Mail" and "Windows Computer" (or your device)
4. Google will generate a 16-character password
5. Use that password in the configuration

### iCloud
1. Go to https://appleid.apple.com/
2. Click "Security"
3. Under "App-specific passwords", click "Generate"
4. Select "Mail" and "Other (custom description)"
5. Use the generated password

### Outlook
- Use your regular password if 2FA is not enabled
- If 2FA is enabled, create an app password at https://account.microsoft.com/security

### ProtonMail
- Use ProtonMail IMAP Bridge on localhost:1143
- See: https://proton.me/support/imap-smtp-bridge

---

## 🛠️ Troubleshooting

### ❌ "Connection refused" or "IMAP login failed"

**Check:**
1. Is the server running? (Terminal 1 should show it's listening)
2. Is your password correct? (Try the app-specific password)
3. Is the IMAP host correct?

**Test directly:**
```bash
python3 << 'EOF'
import imaplib
try:
    imap = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    imap.login('your-email@gmail.com', 'your-app-password')
    print("✅ Connection successful!")
except Exception as e:
    print(f"❌ Error: {e}")
EOF
```

### ❌ "Ollama not running"

**Check if Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

**If not, start it:**
```bash
ollama serve &
```

**Download a model if needed:**
```bash
ollama pull mistral
```

### ❌ "Port 5051 already in use"

**Find what's using it:**
```bash
lsof -i :5051
```

**Kill the process:**
```bash
kill -9 <PID>
```

**Or use a different port by editing `app.py`:**
```python
app.run(host="0.0.0.0", port=5052, debug=False)
```

### ❌ "SSL certificate error"

This usually means the IMAP host or port is wrong. Try:
- Gmail: `imap.gmail.com:993`
- iCloud: `imap.mail.me.com:993`
- Outlook: `outlook.office365.com:993`

---

## 📊 Understanding the API

### Configuration Endpoints

**GET /api/status** — Check system status
```bash
curl http://localhost:5051/api/status | jq
```

**POST /api/setup** — Save configuration
```bash
curl -X POST http://localhost:5051/api/setup \
  -H "Content-Type: application/json" \
  -d '{...config...}'
```

**POST /api/mail/test-connection** — Test IMAP credentials
```bash
curl -X POST http://localhost:5051/api/mail/test-connection \
  -H "Content-Type: application/json" \
  -d '{...config...}'
```

**GET /api/mail/status** — Check Mail connection
```bash
curl http://localhost:5051/api/mail/status | jq
```

### Pipeline Endpoints

**POST /api/pipeline/run** — Start email classification
```bash
curl -X POST http://localhost:5051/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"max_emails": 30}'
```

**GET /api/pipeline/status** — Check pipeline progress
```bash
curl http://localhost:5051/api/pipeline/status | jq
```

### Email Endpoints

**GET /api/emails** — List classified emails
```bash
curl "http://localhost:5051/api/emails?limit=50&category=work" | jq
```

**GET /api/emails/{id}** — Get full email details
```bash
curl http://localhost:5051/api/emails/123 | jq
```

### Action Endpoints

**GET /api/actions** — List pending actions
```bash
curl http://localhost:5051/api/actions | jq
```

**POST /api/actions/{id}/approve** — Approve an action
```bash
curl -X POST http://localhost:5051/api/actions/1/approve \
  -H "Content-Type: application/json" \
  -d '{}'
```

**POST /api/actions/{id}/reject** — Reject an action
```bash
curl -X POST http://localhost:5051/api/actions/1/reject \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 🎯 Common Workflows

### Workflow 1: Auto-Archive Spam

1. Configure with `"auto_archive_spam": "true"`
2. Run pipeline: `POST /api/pipeline/run`
3. High-confidence spam automatically archived
4. Other emails queued for review

### Workflow 2: Manual Review & Approval

1. Configure with `"require_approval": "true"`
2. Run pipeline: `POST /api/pipeline/run`
3. All actions queued (not executed)
4. Review each action: `GET /api/actions`
5. Approve/reject individually: `POST /api/actions/{id}/approve`

### Workflow 3: Daily Digest

1. Configure with `"daily_summary": "true"`
2. Summaries generated after each pipeline run
3. View summaries: `GET /api/summaries`
4. Get full summary: `GET /api/summaries/{id}`

### Workflow 4: Bulk Actions

1. Get pending actions: `GET /api/actions`
2. Approve multiple: `POST /api/actions/bulk`
```bash
curl -X POST http://localhost:5051/api/actions/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "ids": [1, 2, 3, 4, 5],
    "action_type": "archive"
  }'
```

---

## 📝 Configuration Options Explained

```json
{
  "mail_imap_host": "imap.gmail.com",          # IMAP server address
  "mail_imap_port": "993",                     # IMAP port (993 = SSL/TLS)
  "mail_imap_username": "user@gmail.com",      # Email address
  "mail_imap_password": "app-password",        # App-specific password
  "mail_account_name": "Gmail",                # Display name for this account
  
  "ollama_model": "mistral",                   # LLM model to use
  "ollama_url": "http://localhost:11434",      # Ollama API URL
  
  "auto_archive_spam": "true",                 # Auto-archive high-confidence spam?
  "auto_unsubscribe": "false",                 # Auto-unsubscribe from lists?
  "require_approval": "true",                  # Queue all actions for approval?
  "auto_threshold": "0.90",                    # Confidence threshold (0-1) for auto-actions
  "rate_limit_per_run": "10",                  # Max auto-actions per pipeline run
  
  "daily_summary": "true",                     # Generate daily summary?
  "daily_summary_time": "08:00",               # What time (HH:MM)?
  "weekly_summary": "false",                   # Generate weekly summary?
  "weekly_summary_day": "monday"               # Which day?
}
```

---

## 🔐 Security Best Practices

✅ **DO:**
- Use app-specific passwords (not your main password)
- Enable full-disk encryption on your Mac
- Back up `gmail_ai.db` regularly
- Keep Ollama updated

❌ **DON'T:**
- Share your `gmail_ai.db` file
- Commit credentials to Git
- Use simple passwords
- Run on unsecured networks

---

## 🚀 Next Steps

### After First Test:
1. Try with different IMAP providers (Gmail, iCloud, Outlook, ProtonMail)
2. Test with different AI models (mistral, neural-chat, etc.)
3. Adjust classification thresholds based on accuracy
4. Test all action types (archive, trash, flag, read)

### For Production:
1. Set up systemd service to auto-start Flask server
2. Create UI dashboard (future phase)
3. Add email templates for auto-replies
4. Set up scheduled pipeline runs

### Advanced:
1. Multi-account support
2. Custom classification rules
3. Email analytics dashboard
4. Integration with calendar system

---

## 📞 Need Help?

**Check the full test report:**
```bash
open /Volumes/EXTERNAL/MYLLM/PHASE4_TEST_REPORT.md
```

**Check the setup guide:**
```bash
open /Volumes/EXTERNAL/MYLLM/MAIL_AI_SETUP.md
```

**Check logs:**
```bash
# Flask console output (in original terminal)
tail -f /Volumes/EXTERNAL/MYLLM/gmail-ai-manager/gmail_ai.db
```

---

## 🎉 You're Ready!

Your Mail AI Manager is fully functional and ready to test. Start with the 5-minute quick start above, then explore the API endpoints based on your needs.

**Enjoy automated email management! 📧✨**

---

*Last Updated: March 27, 2026*  
*Version: Phase 4 Complete*  
*Status: ✅ Production Ready*
