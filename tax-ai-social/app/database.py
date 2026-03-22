import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "posts.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            specialty TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            compliance_passed INTEGER DEFAULT 0,
            meta_post_id TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            approved_at TEXT,
            posted_at TEXT,
            rejected_at TEXT,
            reject_reason TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            action TEXT,
            detail TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()

def save_post(platform, specialty, content, compliance_passed):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO posts (platform, specialty, content, status, compliance_passed) VALUES (?, ?, ?, 'draft', ?)",
        (platform, specialty, content, 1 if compliance_passed else 0)
    )
    post_id = c.lastrowid
    conn.commit()
    conn.close()
    log_action(post_id, "GENERATED", f"Platform: {platform} | Specialty: {specialty} | Compliance: {compliance_passed}")
    return post_id

def get_drafts():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE status='draft' ORDER BY created_at DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_all_posts(limit=50):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM posts ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_post(post_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE id=?", (post_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def approve_post(post_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE posts SET status='approved', approved_at=? WHERE id=?",
              (datetime.now().isoformat(), post_id))
    conn.commit()
    conn.close()
    log_action(post_id, "APPROVED", "Post approved for publishing")

def mark_posted(post_id, meta_post_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE posts SET status='posted', posted_at=?, meta_post_id=? WHERE id=?",
              (datetime.now().isoformat(), meta_post_id, post_id))
    conn.commit()
    conn.close()
    log_action(post_id, "POSTED", f"Meta Post ID: {meta_post_id}")

def reject_post(post_id, reason=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE posts SET status='rejected', rejected_at=?, reject_reason=? WHERE id=?",
              (datetime.now().isoformat(), reason, post_id))
    conn.commit()
    conn.close()
    log_action(post_id, "REJECTED", reason)

def edit_post(post_id, new_content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE posts SET content=? WHERE id=?", (new_content, post_id))
    conn.commit()
    conn.close()
    log_action(post_id, "EDITED", "Content updated manually")

def mark_failed(post_id, error):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE posts SET status='failed' WHERE id=?", (post_id,))
    conn.commit()
    conn.close()
    log_action(post_id, "FAILED", error)

def log_action(post_id, action, detail=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO audit_log (post_id, action, detail) VALUES (?, ?, ?)",
              (post_id, action, detail))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    stats = {}
    for status in ['draft', 'approved', 'posted', 'rejected', 'failed']:
        c.execute("SELECT COUNT(*) FROM posts WHERE status=?", (status,))
        stats[status] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM posts")
    stats['total'] = c.fetchone()[0]
    conn.close()
    return stats
