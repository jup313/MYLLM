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

    conn.commit()
    conn.close()
    print("✅ Database initialized")


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
         labels, category, confidence, llm_action, draft_reply, unsubscribe_url, processed)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        email.get("id"), email.get("thread_id"), email.get("subject"),
        email.get("sender"), email.get("sender_email"), email.get("snippet"),
        email.get("body"), email.get("date"), email.get("labels"),
        email.get("category"), email.get("confidence"),
        email.get("llm_action"), email.get("draft_reply"),
        email.get("unsubscribe_url"), email.get("processed", 0)
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
