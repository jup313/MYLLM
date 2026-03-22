#!/usr/bin/env python3
"""
gmail_client.py — Gmail API OAuth2 client
Handles auth, fetching, labeling, archiving, drafts, sending.
"""

import os
import json
import base64
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from database import get_config, log_action

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.labels",
]

TOKEN_PATH   = Path(__file__).parent / "token.json"
CREDS_PATH   = Path(__file__).parent / "credentials.json"


# ── Auth ─────────────────────────────────────────────────────────────

def _make_credentials_dict() -> dict:
    """Build credentials.json content from DB config."""
    client_id     = get_config("gmail_client_id", "")
    client_secret = get_config("gmail_client_secret", "")
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
        }
    }


def write_credentials_file():
    """Write credentials.json from DB settings."""
    cred_dict = _make_credentials_dict()
    CREDS_PATH.write_text(json.dumps(cred_dict, indent=2))
    return CREDS_PATH


def get_service():
    """Return authenticated Gmail API service."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                write_credentials_file()
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def is_authenticated() -> bool:
    """Check if token.json exists and is valid."""
    if not TOKEN_PATH.exists():
        return False
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if creds and creds.valid:
            return True
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
            return True
    except Exception:
        pass
    return False


def get_auth_url() -> str:
    """Get OAuth2 authorization URL (for web flow)."""
    write_credentials_file()
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDS_PATH), SCOPES,
        redirect_uri="http://localhost:5050/oauth2callback"
    )
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return auth_url


def exchange_code(code: str):
    """Exchange OAuth2 code for tokens."""
    write_credentials_file()
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDS_PATH), SCOPES,
        redirect_uri="http://localhost:5050/oauth2callback"
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    TOKEN_PATH.write_text(creds.to_json())
    return True


# ── Email parsing ─────────────────────────────────────────────────────

def _decode_body(payload) -> str:
    """Recursively extract plain text body from MIME payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    if payload.get("mimeType") == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            raw = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            # Strip HTML tags roughly
            import re
            return re.sub(r"<[^>]+>", " ", raw)
    for part in payload.get("parts", []):
        text = _decode_body(part)
        if text:
            return text
    return ""


def _parse_message(msg) -> dict:
    """Parse a Gmail message into a clean dict."""
    headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
    sender_raw = headers.get("from", "")
    # Extract email from "Name <email>" format
    import re
    match = re.search(r"<(.+?)>", sender_raw)
    sender_email = match.group(1) if match else sender_raw.strip()
    sender_name  = re.sub(r"<.+?>", "", sender_raw).strip().strip('"')

    # Extract unsubscribe URL from headers
    unsubscribe_header = headers.get("list-unsubscribe", "")
    unsubscribe_url = None
    if unsubscribe_header:
        url_match = re.search(r"<(https?://[^>]+)>", unsubscribe_header)
        mailto_match = re.search(r"<(mailto:[^>]+)>", unsubscribe_header)
        if url_match:
            unsubscribe_url = url_match.group(1)
        elif mailto_match:
            unsubscribe_url = mailto_match.group(1)

    body = _decode_body(msg["payload"])
    snippet = msg.get("snippet", "")

    # Parse date
    date_str = headers.get("date", "")
    try:
        from email.utils import parsedate_to_datetime
        date_obj = parsedate_to_datetime(date_str)
        date_iso = date_obj.isoformat()
    except Exception:
        date_iso = date_str

    return {
        "id":              msg["id"],
        "thread_id":       msg["threadId"],
        "subject":         headers.get("subject", "(no subject)"),
        "sender":          sender_name or sender_email,
        "sender_email":    sender_email,
        "snippet":         snippet,
        "body":            body[:3000],  # Limit to 3k chars for LLM
        "date":            date_iso,
        "labels":          json.dumps(msg.get("labelIds", [])),
        "unsubscribe_url": unsubscribe_url,
        "processed":       0,
    }


# ── Fetch emails ──────────────────────────────────────────────────────

def fetch_unread(max_results: int = 50) -> list:
    """Fetch unread emails from Gmail."""
    service = get_service()
    result  = service.users().messages().list(
        userId="me", q="is:unread", maxResults=max_results
    ).execute()

    messages = result.get("messages", [])
    emails   = []
    for m in messages:
        try:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="full"
            ).execute()
            parsed = _parse_message(msg)
            emails.append(parsed)
        except Exception as e:
            print(f"  ⚠️  Error parsing {m['id']}: {e}")
    return emails


def fetch_recent(max_results: int = 30) -> list:
    """Fetch recent emails (all, not just unread)."""
    service = get_service()
    result  = service.users().messages().list(
        userId="me", maxResults=max_results
    ).execute()
    messages = result.get("messages", [])
    emails   = []
    for m in messages:
        try:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="full"
            ).execute()
            parsed = _parse_message(msg)
            emails.append(parsed)
        except Exception as e:
            print(f"  ⚠️  Error parsing {m['id']}: {e}")
    return emails


# ── Actions ───────────────────────────────────────────────────────────

def archive_email(email_id: str) -> bool:
    """Remove INBOX label (archive)."""
    try:
        service = get_service()
        service.users().messages().modify(
            userId="me", id=email_id,
            body={"removeLabelIds": ["INBOX"]}
        ).execute()
        log_action(email_id, "archive", "success")
        return True
    except Exception as e:
        log_action(email_id, "archive", "error", str(e))
        return False


def trash_email(email_id: str) -> bool:
    """Move email to trash."""
    try:
        service = get_service()
        service.users().messages().trash(userId="me", id=email_id).execute()
        log_action(email_id, "trash", "success")
        return True
    except Exception as e:
        log_action(email_id, "trash", "error", str(e))
        return False


def mark_read(email_id: str) -> bool:
    """Mark email as read."""
    try:
        service = get_service()
        service.users().messages().modify(
            userId="me", id=email_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return True
    except Exception as e:
        return False


def apply_label(email_id: str, label_name: str) -> bool:
    """Apply a Gmail label (creates it if missing)."""
    try:
        service = get_service()
        # Get or create label
        labels_result = service.users().labels().list(userId="me").execute()
        label_id = None
        for lbl in labels_result.get("labels", []):
            if lbl["name"].lower() == label_name.lower():
                label_id = lbl["id"]
                break
        if not label_id:
            new_label = service.users().labels().create(
                userId="me", body={"name": label_name}
            ).execute()
            label_id = new_label["id"]
        service.users().messages().modify(
            userId="me", id=email_id,
            body={"addLabelIds": [label_id]}
        ).execute()
        log_action(email_id, f"label:{label_name}", "success")
        return True
    except Exception as e:
        log_action(email_id, f"label:{label_name}", "error", str(e))
        return False


def create_draft(to: str, subject: str, body: str, reply_to_id: str = None) -> dict:
    """Create a Gmail draft."""
    try:
        service = get_service()
        message = MIMEText(body)
        message["to"]      = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        draft_body = {"message": {"raw": raw}}
        if reply_to_id:
            draft_body["message"]["threadId"] = reply_to_id
        draft = service.users().drafts().create(
            userId="me", body=draft_body
        ).execute()
        log_action(reply_to_id or "new", "create_draft", "success",
                   f"to={to} subject={subject[:50]}")
        return {"success": True, "draft_id": draft["id"]}
    except Exception as e:
        log_action(reply_to_id or "new", "create_draft", "error", str(e))
        return {"success": False, "error": str(e)}


def send_email(to: str, subject: str, body: str, thread_id: str = None) -> dict:
    """Send an email via Gmail API."""
    try:
        service  = get_service()
        message  = MIMEText(body)
        message["to"]      = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        msg_body = {"raw": raw}
        if thread_id:
            msg_body["threadId"] = thread_id
        sent = service.users().messages().send(
            userId="me", body=msg_body
        ).execute()
        log_action(thread_id or "new", "send_email", "success",
                   f"to={to} subject={subject[:50]}")
        return {"success": True, "message_id": sent["id"]}
    except Exception as e:
        log_action(thread_id or "new", "send_email", "error", str(e))
        return {"success": False, "error": str(e)}


def get_labels() -> list:
    """Get all Gmail labels."""
    try:
        service = get_service()
        result  = service.users().labels().list(userId="me").execute()
        return result.get("labels", [])
    except Exception:
        return []
