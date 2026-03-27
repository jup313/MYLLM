#!/usr/bin/env python3
"""
app.py — Flask web server for Mail AI Manager
Universal IMAP email manager with Ollama LLM integration
"""

import os
import threading
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, redirect
from flask_cors import CORS

import database as db
from database import (
    init_db, get_config, set_config, get_all_config,
    is_configured, get_emails, get_email,
    get_pending_actions, complete_action, reject_action,
    get_audit_log, get_stats, get_summaries, get_summary
)

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

BASE_DIR   = Path(__file__).parent
TOKEN_PATH = BASE_DIR / "token.json"

# ── Startup ──────────────────────────────────────────────────────────

@app.before_request
def ensure_db():
    init_db()


# ── Static / UI ──────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_file(str(BASE_DIR / "index.html"))


# ── Setup API ────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    """Check overall system status."""
    from llm_engine import check_ollama
    from gmail_client import is_authenticated
    ollama = check_ollama()
    return jsonify({
        "configured":     is_configured(),
        "authenticated":  is_authenticated(),
        "ollama_running": ollama["running"],
        "ollama_models":  ollama.get("models", []),
        "config":         {k: v for k, v in get_all_config().items()
                           if k not in ("gmail_client_secret",)},
    })


@app.route("/api/setup", methods=["POST"])
def api_setup():
    """Save all configuration from setup form."""
    data = request.get_json() or {}

    required = ["gmail_client_id", "gmail_client_secret", "gmail_address", "ollama_model"]
    missing  = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({"success": False, "error": f"Missing fields: {', '.join(missing)}"}), 400

    # Save all config fields
    fields = [
        "gmail_client_id", "gmail_client_secret", "gmail_address",
        "ollama_model", "ollama_url",
        "auto_archive_spam", "auto_unsubscribe", "require_approval",
        "auto_threshold", "rate_limit_per_run",
        "daily_summary", "daily_summary_time",
        "weekly_summary", "weekly_summary_day",
        "send_summary_email",
    ]
    for field in fields:
        if field in data:
            set_config(field, str(data[field]))

    # Set defaults for missing optional fields
    defaults = {
        "ollama_url":         "http://localhost:11434",
        "auto_archive_spam":  "true",
        "auto_unsubscribe":   "false",
        "require_approval":   "true",
        "auto_threshold":     "0.90",
        "rate_limit_per_run": "10",
        "daily_summary":      "true",
        "daily_summary_time": "08:00",
        "weekly_summary":     "false",
        "weekly_summary_day": "monday",
    }
    for k, v in defaults.items():
        if not get_config(k):
            set_config(k, v)

    return jsonify({"success": True, "message": "Configuration saved"})


@app.route("/api/mail/test-connection", methods=["POST"])
def api_mail_test_connection():
    """Test IMAP connection with provided credentials."""
    data = request.get_json() or {}
    
    required = ["imap_host", "imap_port", "email_address", "imap_password"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({"success": False, "error": f"Missing fields: {', '.join(missing)}"}), 400
    
    try:
        import imaplib
        host = data.get("imap_host")
        port = int(data.get("imap_port", 993))
        email = data.get("email_address")
        password = data.get("imap_password")
        
        # Attempt IMAP connection
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(email, password)
        mail.logout()
        
        return jsonify({
            "success": True,
            "message": f"Successfully connected to {host}:{port}",
            "provider": data.get("provider", "Unknown")
        })
    except imaplib.IMAP4.error as e:
        return jsonify({"success": False, "error": f"IMAP error: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Connection failed: {str(e)}"}), 400


# ── Gmail OAuth ───────────────────────────────────────────────────────

@app.route("/api/auth/start")
def api_auth_start():
    """Start Gmail OAuth2 flow."""
    try:
        from gmail_client import get_auth_url, write_credentials_file
        write_credentials_file()
        url = get_auth_url()
        return jsonify({"success": True, "auth_url": url})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/oauth2callback")
def oauth2_callback():
    """Handle OAuth2 callback from Google."""
    code  = request.args.get("code")
    error = request.args.get("error")
    if error:
        return redirect(f"/?auth_error={error}")
    if not code:
        return redirect("/?auth_error=no_code")
    try:
        from gmail_client import exchange_code
        exchange_code(code)
        return redirect("/?auth_success=1")
    except Exception as e:
        return redirect(f"/?auth_error={str(e)[:100]}")


@app.route("/api/auth/status")
def api_auth_status():
    from gmail_client import is_authenticated
    return jsonify({"authenticated": is_authenticated()})


@app.route("/api/auth/revoke", methods=["POST"])
def api_auth_revoke():
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
    return jsonify({"success": True})


# ── Pipeline ─────────────────────────────────────────────────────────

_pipeline_status = {"running": False, "stats": None, "error": None}


def _run_pipeline_thread(max_emails: int):
    global _pipeline_status
    try:
        from action_engine import run_pipeline
        stats = run_pipeline(max_emails=max_emails)
        _pipeline_status = {"running": False, "stats": stats, "error": None}
    except Exception as e:
        _pipeline_status = {"running": False, "stats": None, "error": str(e)}


@app.route("/api/pipeline/run", methods=["POST"])
def api_pipeline_run():
    global _pipeline_status
    if _pipeline_status["running"]:
        return jsonify({"success": False, "error": "Pipeline already running"}), 409
    data = request.get_json() or {}
    max_emails = int(data.get("max_emails", 30))
    _pipeline_status = {"running": True, "stats": None, "error": None}
    thread = threading.Thread(target=_run_pipeline_thread, args=(max_emails,), daemon=True)
    thread.start()
    return jsonify({"success": True, "message": f"Pipeline started (max {max_emails} emails)"})


@app.route("/api/pipeline/status")
def api_pipeline_status():
    return jsonify(_pipeline_status)


# ── Emails ───────────────────────────────────────────────────────────

@app.route("/api/emails")
def api_emails():
    limit     = int(request.args.get("limit", 50))
    processed = request.args.get("processed")
    category  = request.args.get("category")
    if processed is not None:
        processed = int(processed)
    emails = get_emails(limit=limit, processed=processed, category=category)
    # Don't send full body in list view
    for e in emails:
        e["body"] = (e.get("body") or "")[:200]
    return jsonify({"emails": emails, "count": len(emails)})


@app.route("/api/emails/<email_id>")
def api_email_detail(email_id):
    email = get_email(email_id)
    if not email:
        return jsonify({"error": "Not found"}), 404
    return jsonify(email)


@app.route("/api/emails/<email_id>/draft", methods=["POST"])
def api_regenerate_draft(email_id):
    """Re-generate a draft reply for an email."""
    email = get_email(email_id)
    if not email:
        return jsonify({"error": "Not found"}), 404
    from llm_engine import draft_reply
    reply = draft_reply(email)
    from database import get_conn
    conn = db.get_conn()
    conn.execute("UPDATE emails SET draft_reply = ? WHERE id = ?", (reply, email_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "draft_reply": reply})


# ── Actions ───────────────────────────────────────────────────────────

@app.route("/api/actions")
def api_actions():
    actions = get_pending_actions(limit=100)
    return jsonify({"actions": actions, "count": len(actions)})


@app.route("/api/actions/<int:action_id>/approve", methods=["POST"])
def api_approve_action(action_id):
    data    = request.get_json() or {}
    actions = {a["id"]: a for a in get_pending_actions(1000)}
    action  = actions.get(action_id)
    if not action:
        return jsonify({"error": "Action not found"}), 404

    from action_engine import execute_action
    result = execute_action(
        action_id,
        action["action_type"],
        action["email_id"],
        custom_body=data.get("body")
    )
    return jsonify(result)


@app.route("/api/actions/<int:action_id>/reject", methods=["POST"])
def api_reject_action(action_id):
    reject_action(action_id)
    return jsonify({"success": True})


@app.route("/api/actions/bulk", methods=["POST"])
def api_bulk_actions():
    data       = request.get_json() or {}
    action_ids = data.get("ids", [])
    action_type = data.get("action_type", "")
    from action_engine import bulk_execute
    result = bulk_execute(action_ids, action_type)
    return jsonify(result)


# ── Summaries ─────────────────────────────────────────────────────────

@app.route("/api/summary/daily", methods=["POST"])
def api_daily_summary():
    try:
        from summarizer import generate_daily_summary
        result = generate_daily_summary()
        return jsonify({"success": True, "count": result["count"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/summary/weekly", methods=["POST"])
def api_weekly_summary():
    try:
        from summarizer import generate_weekly_summary
        result = generate_weekly_summary()
        return jsonify({"success": True, "count": result["count"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/summaries")
def api_summaries():
    return jsonify({"summaries": get_summaries(limit=20)})


@app.route("/api/summaries/<int:summary_id>")
def api_summary_detail(summary_id):
    s = get_summary(summary_id)
    if not s:
        return jsonify({"error": "Not found"}), 404
    return jsonify(s)


# ── Stats + Logs ─────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.route("/api/logs")
def api_logs():
    limit = int(request.args.get("limit", 100))
    return jsonify({"logs": get_audit_log(limit=limit)})


# ── Calendar ─────────────────────────────────────────────────────────

@app.route("/api/calendar/status")
def api_calendar_status():
    """Check if Google Calendar is authorized."""
    try:
        from calendar_engine import is_calendar_authorized
        authorized = is_calendar_authorized()
        return jsonify({"authorized": authorized})
    except Exception as e:
        return jsonify({"authorized": False, "error": str(e)})


@app.route("/api/calendar/events")
def api_calendar_events():
    """Get upcoming calendar events (next 7 days)."""
    try:
        from calendar_engine import get_upcoming_events
        days = int(request.args.get("days", 7))
        events = get_upcoming_events(days=days)
        return jsonify({"events": events, "count": len(events)})
    except Exception as e:
        return jsonify({"error": str(e), "events": []}), 500


@app.route("/api/calendar/detect/<email_id>")
def api_calendar_detect(email_id):
    """Check if an email contains meeting/appointment language."""
    email = get_email(email_id)
    if not email:
        return jsonify({"error": "Not found"}), 404
    try:
        from calendar_engine import has_meeting_language
        body = (email.get("body") or "") + " " + (email.get("subject") or "")
        detected = has_meeting_language(body)
        return jsonify({"email_id": email_id, "has_meeting": detected})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/calendar/create/<email_id>", methods=["POST"])
def api_calendar_create_from_email(email_id):
    """
    Extract event details from email using LLM and create a Google Calendar event.
    """
    email = get_email(email_id)
    if not email:
        return jsonify({"error": "Not found"}), 404
    try:
        from calendar_engine import create_event_from_email
        result = create_event_from_email(email)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/calendar/create", methods=["POST"])
def api_calendar_create_manual():
    """
    Manually create a calendar event.
    Body: { title, date, time, duration_hours, location, description }
    """
    data = request.get_json() or {}
    title = data.get("title")
    if not title:
        return jsonify({"success": False, "error": "title is required"}), 400
    try:
        from calendar_engine import create_calendar_event
        result = create_calendar_event(
            title=title,
            date=data.get("date"),
            time=data.get("time"),
            duration_hours=float(data.get("duration_hours", 1)),
            location=data.get("location"),
            description=data.get("description"),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── LLM ──────────────────────────────────────────────────────────────

@app.route("/api/llm/models")
def api_llm_models():
    from llm_engine import check_ollama
    return jsonify(check_ollama())


@app.route("/api/llm/classify", methods=["POST"])
def api_llm_classify():
    """Classify a single email on demand."""
    data = request.get_json() or {}
    email_id = data.get("email_id")
    if email_id:
        email = get_email(email_id)
    else:
        email = data  # Inline email object
    if not email:
        return jsonify({"error": "No email provided"}), 400
    from llm_engine import classify_email
    result = classify_email(email)
    return jsonify(result)


# ── Main ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════╗
║   📧 Mail AI Manager                           ║
║   Universal IMAP Email Manager                 ║
║   Open: http://localhost:5051                  ║
╚══════════════════════════════════════════════════╝
""")
    init_db()
    app.run(host="0.0.0.0", port=5051, debug=False)
