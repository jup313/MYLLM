#!/usr/bin/env python3
"""
database.py — SQLite storage for Gmail AI Manager
Tables: config, emails, actions, logs, contacts
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "gmail_ai.db"

PROVIDER_TEMPLATES = {
    "gmail": {
        "name": "Gmail",
        "imap_host": "imap.gmail.com", "imap_port": 993,
        "smtp_host": "smtp.gmail.com", "smtp_port": 587,
        "notes": "Requires App Password (Google Account → Security → App Passwords)"
    },
    "icloud": {
        "name": "iCloud",
        "imap_host": "imap.mail.me.com", "imap_port": 993,
        "smtp_host": "smtp.mail.me.com", "smtp_port": 587,
        "notes": "Requires App-Specific Password (appleid.apple.com → Sign-In → App-Specific Passwords)"
    },
    "outlook": {
        "name": "Outlook / Hotmail",
        "imap_host": "outlook.office365.com", "imap_port": 993,
        "smtp_host": "smtp.office365.com", "smtp_port": 587,
        "notes": "Use your regular Outlook password or App Password if 2FA enabled"
    },
    "yahoo": {
        "name": "Yahoo Mail",
        "imap_host": "imap.mail.yahoo.com", "imap_port": 993,
        "smtp_host": "smtp.mail.yahoo.com", "smtp_port": 587,
        "notes": "Requires App Password (Yahoo Account → Security → App Password)"
    },
    "custom": {
        "name": "Custom IMAP",
        "imap_host": "", "imap_port": 993,
        "smtp_host": "", "smtp_port": 587,
        "notes": "Enter your provider's IMAP and SMTP server details"
    },
}


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize all tables."""
    conn = get_conn()
    c = conn.cursor()

    # ── Config (key-value settings) ─────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Emails (fetched + classified) ───────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id              TEXT PRIMARY KEY,
            thread_id       TEXT,
            subject         TEXT,
            sender          TEXT,
            sender_email    TEXT,
            snippet         TEXT,
            body            TEXT,
            date            TEXT,
            labels          TEXT,
            category        TEXT,
            confidence      REAL,
            llm_action      TEXT,
            draft_reply     TEXT,
            unsubscribe_url TEXT,
            processed       INTEGER DEFAULT 0,
            fetched_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Actions (pending / completed) ───────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id    TEXT,
            action_type TEXT,
            status      TEXT DEFAULT 'pending',
            notes       TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            executed_at TEXT
        )
    """)

    # ── Audit Log ───────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id   TEXT,
            action     TEXT,
            result     TEXT,
            details    TEXT,
            timestamp  TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Summaries ───────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            type       TEXT,
            date       TEXT,
            html       TEXT,
            text       TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Email Accounts (multi-provider) ─────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS email_accounts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT,
            email       TEXT NOT NULL,
            provider    TEXT DEFAULT 'custom',
            imap_host   TEXT,
            imap_port   INTEGER DEFAULT 993,
            imap_user   TEXT,
            imap_pass   TEXT,
            smtp_host   TEXT,
            smtp_port   INTEGER DEFAULT 587,
            smtp_user   TEXT,
            smtp_pass   TEXT,
            enabled     INTEGER DEFAULT 1,
            last_sync   TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Feedback (user corrections for LLM learning) ────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id              TEXT,
            sender_email          TEXT,
            original_category     TEXT,
            corrected_category    TEXT,
            original_importance   TEXT,
            corrected_importance  TEXT,
            original_action       TEXT,
            corrected_action      TEXT,
            created_at            TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Sender Rules (auto-learned from feedback) ───────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS sender_rules (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_email      TEXT,
            sender_domain     TEXT,
            default_category  TEXT,
            default_importance TEXT,
            default_action    TEXT,
            hit_count         INTEGER DEFAULT 1,
            auto_generated    INTEGER DEFAULT 1,
            created_at        TEXT DEFAULT (datetime('now')),
            updated_at        TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Migrate: add new columns to emails if missing ───────────────
    _add_column_if_missing(c, "emails", "importance", "TEXT")
    _add_column_if_missing(c, "emails", "importance_reason", "TEXT")
    _add_column_if_missing(c, "emails", "account_id", "INTEGER")
    _add_column_if_missing(c, "emails", "user_corrected", "INTEGER DEFAULT 0")
    _add_column_if_missing(c, "emails", "body_html", "TEXT")

    conn.commit()
    conn.close()
    print("✅ Database initialized")


def _add_column_if_missing(cursor, table, column, col_type):
    """Safely add a column to a table if it doesn't exist."""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except sqlite3.OperationalError:
        pass  # Column already exists


# ── Config helpers ──────────────────────────────────────────────────

def set_config(key: str, value):
    """Save a config value (string or dict → JSON)."""
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, str(value))
    )
    conn.commit()
    conn.close()


def get_config(key: str, default=None):
    """Get a config value."""
    conn = get_conn()
    row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row is None:
        return default
    val = row["value"]
    try:
        return json.loads(val)
    except Exception:
        return val


def get_all_config() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT key, value FROM config").fetchall()
    conn.close()
    result = {}
    for r in rows:
        try:
            result[r["key"]] = json.loads(r["value"])
        except Exception:
            result[r["key"]] = r["value"]
    return result


def is_configured() -> bool:
    """Check if Gmail credentials + LLM are set up."""
    cfg = get_all_config()
    required = ["gmail_client_id", "gmail_client_secret", "gmail_address", "ollama_model"]
    return all(cfg.get(k) for k in required)


# ── Email helpers ───────────────────────────────────────────────────

def save_email(email: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO emails
        (id, thread_id, subject, sender, sender_email, snippet, body, date,
         labels, category, confidence, llm_action, draft_reply, unsubscribe_url,
         processed, importance, importance_reason, account_id, user_corrected, body_html)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        email.get("id"), email.get("thread_id"), email.get("subject"),
        email.get("sender"), email.get("sender_email"), email.get("snippet"),
        email.get("body"), email.get("date"), email.get("labels"),
        email.get("category"), email.get("confidence"),
        email.get("llm_action"), email.get("draft_reply"),
        email.get("unsubscribe_url"), email.get("processed", 0),
        email.get("importance"), email.get("importance_reason"),
        email.get("account_id"), email.get("user_corrected", 0),
        email.get("body_html")
    ))
    conn.commit()
    conn.close()


def get_emails(limit=50, processed=None, category=None):
    conn = get_conn()
    query = "SELECT * FROM emails WHERE 1=1"
    params = []
    if processed is not None:
        query += " AND processed = ?"
        params.append(processed)
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_email(email_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM emails WHERE id = ?", (email_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def mark_processed(email_id: str):
    conn = get_conn()
    conn.execute("UPDATE emails SET processed = 1 WHERE id = ?", (email_id,))
    conn.commit()
    conn.close()


# ── Action helpers ──────────────────────────────────────────────────

def add_action(email_id: str, action_type: str, notes: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO actions (email_id, action_type, notes) VALUES (?, ?, ?)",
        (email_id, action_type, notes)
    )
    conn.commit()
    conn.close()


def get_pending_actions(limit=100):
    conn = get_conn()
    rows = conn.execute("""
        SELECT a.*, e.subject, e.sender, e.sender_email, e.category, e.draft_reply, e.snippet
        FROM actions a LEFT JOIN emails e ON a.email_id = e.id
        WHERE a.status = 'pending'
        ORDER BY a.created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def complete_action(action_id: int, result: str = "done"):
    conn = get_conn()
    conn.execute(
        "UPDATE actions SET status = ?, executed_at = datetime('now') WHERE id = ?",
        (result, action_id)
    )
    conn.commit()
    conn.close()


def reject_action(action_id: int):
    complete_action(action_id, "rejected")


# ── Audit log ───────────────────────────────────────────────────────

def log_action(email_id: str, action: str, result: str, details: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO audit_log (email_id, action, result, details) VALUES (?,?,?,?)",
        (email_id, action, result, details)
    )
    conn.commit()
    conn.close()


def get_audit_log(limit=200):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Summary helpers ─────────────────────────────────────────────────

def save_summary(summary_type: str, html: str, text: str):
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO summaries (type, date, html, text) VALUES (?,?,?,?)",
        (summary_type, today, html, text)
    )
    conn.commit()
    conn.close()


def get_summaries(limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, type, date, created_at FROM summaries ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_summary(summary_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM summaries WHERE id = ?", (summary_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Email Accounts helpers ──────────────────────────────────────────

def add_email_account(account: dict) -> int:
    conn = get_conn()
    c = conn.execute("""
        INSERT INTO email_accounts
        (name, email, provider, imap_host, imap_port, imap_user, imap_pass,
         smtp_host, smtp_port, smtp_user, smtp_pass, enabled)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        account.get("name", ""), account["email"], account.get("provider", "custom"),
        account.get("imap_host"), account.get("imap_port", 993),
        account.get("imap_user", account["email"]), account.get("imap_pass"),
        account.get("smtp_host"), account.get("smtp_port", 587),
        account.get("smtp_user", account["email"]), account.get("smtp_pass"),
        account.get("enabled", 1)
    ))
    account_id = c.lastrowid
    conn.commit()
    conn.close()
    return account_id


def get_email_accounts(enabled_only=False) -> list:
    conn = get_conn()
    q = "SELECT * FROM email_accounts"
    if enabled_only:
        q += " WHERE enabled = 1"
    q += " ORDER BY created_at"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_email_account(account_id: int) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT * FROM email_accounts WHERE id = ?", (account_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_email_account(account_id: int, data: dict):
    conn = get_conn()
    fields = []
    values = []
    for key in ["name", "email", "provider", "imap_host", "imap_port", "imap_user",
                "imap_pass", "smtp_host", "smtp_port", "smtp_user", "smtp_pass", "enabled"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        values.append(account_id)
        conn.execute(f"UPDATE email_accounts SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()


def delete_email_account(account_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM email_accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()


def update_account_last_sync(account_id: int):
    conn = get_conn()
    conn.execute("UPDATE email_accounts SET last_sync = datetime('now') WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()


# ── Feedback helpers ────────────────────────────────────────────────

def save_feedback(email_id: str, sender_email: str,
                  orig_cat: str, new_cat: str,
                  orig_imp: str, new_imp: str,
                  orig_action: str, new_action: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO feedback
        (email_id, sender_email, original_category, corrected_category,
         original_importance, corrected_importance, original_action, corrected_action)
        VALUES (?,?,?,?,?,?,?,?)
    """, (email_id, sender_email, orig_cat, new_cat, orig_imp, new_imp, orig_action, new_action))
    conn.commit()
    conn.close()
    # Auto-update sender rules
    _update_sender_rule(sender_email, new_cat, new_imp, new_action)


def get_feedback(limit=100) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM feedback ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_feedback_for_prompt(limit=10) -> list:
    """Get recent feedback examples to inject into the LLM prompt for few-shot learning."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT f.sender_email, f.corrected_category, f.corrected_importance,
               e.subject, e.sender
        FROM feedback f
        LEFT JOIN emails e ON f.email_id = e.id
        ORDER BY f.created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_feedback_stats() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as c FROM feedback").fetchone()["c"]
    correct = conn.execute("""
        SELECT COUNT(*) as c FROM feedback
        WHERE original_category = corrected_category
          AND original_importance = corrected_importance
    """).fetchone()["c"]
    conn.close()
    accuracy = (correct / total * 100) if total > 0 else 100
    return {"total_corrections": total, "unchanged": correct, "accuracy_pct": round(accuracy, 1)}


# ── Sender Rules helpers ───────────────────────────────────────────

def _update_sender_rule(sender_email: str, category: str, importance: str, action: str):
    """Update or create a sender rule based on user feedback."""
    if not sender_email:
        return
    domain = sender_email.split("@")[-1] if "@" in sender_email else ""
    conn = get_conn()
    existing = conn.execute(
        "SELECT * FROM sender_rules WHERE sender_email = ?", (sender_email,)
    ).fetchone()
    if existing:
        conn.execute("""
            UPDATE sender_rules SET
                default_category = ?, default_importance = ?, default_action = ?,
                hit_count = hit_count + 1, updated_at = datetime('now')
            WHERE sender_email = ?
        """, (category, importance, action, sender_email))
    else:
        conn.execute("""
            INSERT INTO sender_rules
            (sender_email, sender_domain, default_category, default_importance, default_action)
            VALUES (?,?,?,?,?)
        """, (sender_email, domain, category, importance, action))
    conn.commit()
    conn.close()


def get_sender_rule(sender_email: str) -> dict:
    """Get a learned rule for a specific sender."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM sender_rules WHERE sender_email = ?", (sender_email,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_sender_rules(limit=100) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM sender_rules ORDER BY hit_count DESC, updated_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def reclassify_email(email_id: str, category: str = None, importance: str = None,
                     action: str = None) -> dict:
    """Reclassify an email and save feedback."""
    email = get_email(email_id)
    if not email:
        return {"success": False, "error": "Email not found"}
    # Save feedback
    save_feedback(
        email_id=email_id,
        sender_email=email.get("sender_email", ""),
        orig_cat=email.get("category", ""),
        new_cat=category or email.get("category", ""),
        orig_imp=email.get("importance", ""),
        new_imp=importance or email.get("importance", ""),
        orig_action=email.get("llm_action", ""),
        new_action=action or email.get("llm_action", ""),
    )
    # Update the email record
    conn = get_conn()
    updates = ["user_corrected = 1"]
    params = []
    if category:
        updates.append("category = ?")
        params.append(category)
    if importance:
        updates.append("importance = ?")
        params.append(importance)
    if action:
        updates.append("llm_action = ?")
        params.append(action)
    params.append(email_id)
    conn.execute(f"UPDATE emails SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return {"success": True}


# ── Stats ────────────────────────────────────────────────────────────

def get_stats():
    conn = get_conn()
    total   = conn.execute("SELECT COUNT(*) as c FROM emails").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM actions WHERE status='pending'").fetchone()["c"]
    cats    = conn.execute("""
        SELECT category, COUNT(*) as c FROM emails
        WHERE category IS NOT NULL GROUP BY category
    """).fetchall()
    conn.close()
    return {
        "total_emails": total,
        "pending_actions": pending,
        "by_category": {r["category"]: r["c"] for r in cats}
    }


if __name__ == "__main__":
    init_db()
    print("Config:", get_all_config())
    print("Stats:", get_stats())
