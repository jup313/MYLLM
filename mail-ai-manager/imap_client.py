#!/usr/bin/env python3
"""
imap_client.py — Universal IMAP email client
Handles IMAP connections, fetching, and basic operations for any IMAP server.
"""

import imaplib
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime
import json
import re

from database import get_config, log_action


# ── Configuration ────────────────────────────────────────────────────

def get_imap_connection():
    """Get authenticated IMAP connection from config."""
    host = get_config("mail_imap_host")
    port = int(get_config("mail_imap_port", 993))
    email = get_config("mail_imap_username")
    password = get_config("mail_imap_password")
    
    if not all([host, port, email, password]):
        raise ValueError("IMAP credentials not configured")
    
    mail = imaplib.IMAP4_SSL(host, port)
    mail.login(email, password)
    return mail


def is_authenticated() -> bool:
    """Check if IMAP credentials are configured and valid."""
    try:
        mail = get_imap_connection()
        mail.logout()
        return True
    except Exception:
        return False


# ── Email parsing ───────────────────────────────────────────────────

def _parse_message(email_msg) -> dict:
    """Parse an email.message.Message into a clean dict."""
    # Extract headers
    sender = email_msg.get("From", "")
    subject = email_msg.get("Subject", "(no subject)")
    date_str = email_msg.get("Date", "")
    
    # Extract email from "Name <email>" format
    match = re.search(r"<(.+?)>", sender)
    sender_email = match.group(1) if match else sender.strip()
    sender_name = re.sub(r"<.+?>", "", sender).strip().strip('"')
    
    # Extract unsubscribe URL from headers
    unsubscribe_header = email_msg.get("List-Unsubscribe", "")
    unsubscribe_url = None
    if unsubscribe_header:
        url_match = re.search(r"<(https?://[^>]+)>", unsubscribe_header)
        mailto_match = re.search(r"<(mailto:[^>]+)>", unsubscribe_header)
        if url_match:
            unsubscribe_url = url_match.group(1)
        elif mailto_match:
            unsubscribe_url = mailto_match.group(1)
    
    # Extract body
    body = ""
    if email_msg.is_multipart():
        for part in email_msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                try:
                    body = payload.decode("utf-8")
                except:
                    body = payload.decode("iso-8859-1", errors="replace")
                break
            elif content_type == "text/html" and not body:
                payload = part.get_payload(decode=True)
                try:
                    html = payload.decode("utf-8")
                except:
                    html = payload.decode("iso-8859-1", errors="replace")
                # Strip HTML tags roughly
                body = re.sub(r"<[^>]+>", " ", html)
    else:
        payload = email_msg.get_payload(decode=True)
        if payload:
            try:
                body = payload.decode("utf-8")
            except:
                body = payload.decode("iso-8859-1", errors="replace")
    
    # Parse date
    try:
        from email.utils import parsedate_to_datetime
        date_obj = parsedate_to_datetime(date_str)
        date_iso = date_obj.isoformat()
    except Exception:
        date_iso = date_str
    
    snippet = body[:100].replace("\n", " ") if body else ""
    
    return {
        "id": email_msg.get("Message-ID", ""),
        "thread_id": email_msg.get("In-Reply-To", ""),
        "subject": subject,
        "sender": sender_name or sender_email,
        "sender_email": sender_email,
        "snippet": snippet,
        "body": body[:3000],  # Limit to 3k chars for LLM
        "date": date_iso,
        "labels": json.dumps([]),
        "unsubscribe_url": unsubscribe_url,
        "processed": 0,
    }


# ── Fetch emails ─────────────────────────────────────────────────────

def fetch_unread(max_results: int = 50) -> list:
    """Fetch unread emails from IMAP."""
    try:
        mail = get_imap_connection()
        mail.select("INBOX")
        
        # Search for unread emails
        status, message_nums = mail.search(None, "UNSEEN")
        email_ids = message_nums[0].split()[:max_results]
        
        emails = []
        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                email_body = msg_data[0][1]
                email_msg = email_lib.message_from_bytes(email_body)
                parsed = _parse_message(email_msg)
                parsed["id"] = email_id.decode() if isinstance(email_id, bytes) else email_id
                emails.append(parsed)
            except Exception as e:
                print(f"  ⚠️  Error parsing email {email_id}: {e}")
        
        mail.logout()
        return emails
    except Exception as e:
        print(f"  ⚠️  Error fetching unread emails: {e}")
        return []


def fetch_recent(max_results: int = 30) -> list:
    """Fetch recent emails from IMAP."""
    try:
        mail = get_imap_connection()
        mail.select("INBOX")
        
        # Search for all emails
        status, message_nums = mail.search(None, "ALL")
        email_ids = message_nums[0].split()[-max_results:]  # Get last N emails
        
        emails = []
        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                email_body = msg_data[0][1]
                email_msg = email_lib.message_from_bytes(email_body)
                parsed = _parse_message(email_msg)
                parsed["id"] = email_id.decode() if isinstance(email_id, bytes) else email_id
                emails.append(parsed)
            except Exception as e:
                print(f"  ⚠️  Error parsing email {email_id}: {e}")
        
        mail.logout()
        return emails
    except Exception as e:
        print(f"  ⚠️  Error fetching recent emails: {e}")
        return []


# ── Actions ──────────────────────────────────────────────────────────

def archive_email(email_id: str) -> bool:
    """Move email to Archive folder."""
    try:
        mail = get_imap_connection()
        mail.select("INBOX")
        mail.copy(email_id, "Archive")
        mail.store(email_id, "+FLAGS", "\\Deleted")
        mail.expunge()
        mail.logout()
        log_action(email_id, "archive", "success")
        return True
    except Exception as e:
        log_action(email_id, "archive", "error", str(e))
        return False


def trash_email(email_id: str) -> bool:
    """Move email to Trash folder."""
    try:
        mail = get_imap_connection()
        mail.select("INBOX")
        mail.copy(email_id, "Trash")
        mail.store(email_id, "+FLAGS", "\\Deleted")
        mail.expunge()
        mail.logout()
        log_action(email_id, "trash", "success")
        return True
    except Exception as e:
        log_action(email_id, "trash", "error", str(e))
        return False


def mark_read(email_id: str) -> bool:
    """Mark email as read."""
    try:
        mail = get_imap_connection()
        mail.select("INBOX")
        mail.store(email_id, "+FLAGS", "\\Seen")
        mail.logout()
        return True
    except Exception as e:
        return False


def mark_unread(email_id: str) -> bool:
    """Mark email as unread."""
    try:
        mail = get_imap_connection()
        mail.select("INBOX")
        mail.store(email_id, "-FLAGS", "\\Seen")
        mail.logout()
        return True
    except Exception as e:
        return False
