"""
portfolio_db.py — SQLite storage for portfolio positions
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path

DB_PATH = os.getenv("PORTFOLIO_DB", str(Path(__file__).parent / "portfolio.db"))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS positions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT NOT NULL,
            shares      REAL NOT NULL,
            avg_cost    REAL NOT NULL,
            notes       TEXT DEFAULT '',
            added_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker   TEXT NOT NULL UNIQUE,
            notes    TEXT DEFAULT '',
            added_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


# ── Positions ──────────────────────────────────────────────────────────────

def get_positions():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM positions ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_position(ticker: str, shares: float, avg_cost: float, notes: str = ""):
    conn = get_conn()
    # If already exists, update
    existing = conn.execute("SELECT id FROM positions WHERE ticker = ?", (ticker.upper(),)).fetchone()
    if existing:
        conn.execute(
            "UPDATE positions SET shares=?, avg_cost=?, notes=? WHERE ticker=?",
            (shares, avg_cost, notes, ticker.upper())
        )
    else:
        conn.execute(
            "INSERT INTO positions (ticker, shares, avg_cost, notes) VALUES (?,?,?,?)",
            (ticker.upper(), shares, avg_cost, notes)
        )
    conn.commit()
    conn.close()


def delete_position(ticker: str):
    conn = get_conn()
    conn.execute("DELETE FROM positions WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    conn.close()


# ── Watchlist ──────────────────────────────────────────────────────────────

def get_watchlist():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM watchlist ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_to_watchlist(ticker: str, notes: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO watchlist (ticker, notes) VALUES (?,?)",
        (ticker.upper(), notes)
    )
    conn.commit()
    conn.close()


def remove_from_watchlist(ticker: str):
    conn = get_conn()
    conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    conn.close()


# Init on import
init_db()
