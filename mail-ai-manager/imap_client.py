#!/usr/bin/env python3
"""
imap_client.py — Direct IMAP email client using Python imaplib
Fast, reliable access to any IMAP email provider.
Works with Gmail (app password), iCloud, Outlook, Yahoo, etc.
"""

import imaplib
import email
from email.header import decode_header
import re
import html as html_mod
from datetime import datetime, timedelta
from database import get_config, set_config, log_action, get_email_accounts, update_account_last_sync


def _decode_header_value(value):
    """Decode an email header value."""
    if value is None:
        return ""
    decoded_parts = decode_header(value)
    result = ""
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                result += part.decode(charset or "utf-8", errors="replace")
            except (LookupError, UnicodeDecodeError):
                result += part.decode("utf-8", errors="replace")
        else:
            result += str(part)
    return result


def _html_to_text(html_content):
    """Convert HTML to clean plain text, properly handling tags, entities, and tracking pixels."""
    text = html_content
    # Remove style/script/head blocks entirely
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<head[^>]*>.*?</head>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    # Remove invisible tracking pixels (1x1, 2x6, etc.)
    text = re.sub(r'<img[^>]*(?:width\s*=\s*"[012]"|height\s*=\s*"[012]")[^>]*/?>', '', text, flags=re.IGNORECASE)
    # Replace block elements with newlines
    text = re.sub(r'<br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(?:p|div|tr|li|h[1-6])>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<(?:p|div|tr|li|h[1-6])\b[^>]*>', '\n', text, flags=re.IGNORECASE)
    # Extract link text: <a href="url">text</a> → text
    text = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode HTML entities (&#160;, &amp;, &nbsp;, etc.)
    text = html_mod.unescape(text)
    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _get_connection():
    """Create and return an authenticated IMAP connection."""
    host = get_config("mail_imap_host")
    port = int(get_config("mail_imap_port") or 993)
    username = get_config("mail_imap_username")
    password = get_config("mail_imap_password")

    if not all([host, username, password]):
        raise Exception("IMAP not configured. Please set up IMAP credentials.")

    imap = imaplib.IMAP4_SSL(host, port)
    imap.login(username, password)
    return imap


def is_authenticated() -> bool:
    """Check if IMAP credentials are configured and valid."""
    try:
        imap = _get_connection()
        imap.logout()
        return True
    except Exception:
        return False


def test_mail_connection() -> dict:
    """Test IMAP connection."""
    try:
        host = get_config("mail_imap_host")
        username = get_config("mail_imap_username")
        imap = _get_connection()
        # Get mailbox list
        status, mailboxes = imap.list()
        mailbox_count = len(mailboxes) if mailboxes else 0
        # Get inbox message count
        imap.select("INBOX", readonly=True)
        status, messages = imap.search(None, "ALL")
        msg_count = len(messages[0].split()) if messages[0] else 0
        imap.logout()
        return {
            "success": True,
            "message": f"Connected to {host} as {username} — {msg_count} messages in INBOX",
            "accounts": [f"{username} ({host})"],
            "message_count": msg_count
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _parse_email_message(msg_data, msg_id_str):
    """Parse a raw email message into our standard dict format."""
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    # Subject
    subject = _decode_header_value(msg.get("Subject", "(no subject)"))

    # Sender
    sender_raw = _decode_header_value(msg.get("From", ""))
    match = re.search(r"<(.+?)>", sender_raw)
    sender_email = match.group(1) if match else sender_raw
    sender_name = re.sub(r"<.+?>", "", sender_raw).strip().strip('"').strip("'")

    # Date
    date_str = msg.get("Date", "")

    # Message-ID for unique identification
    message_id = msg.get("Message-ID", msg_id_str)

    # Get body text — preserve both plain text and raw HTML
    body = ""
    body_html = ""
    snippet = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain" and not body:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                except Exception:
                    pass
            elif content_type == "text/html" and not body_html:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body_html = part.get_payload(decode=True).decode(charset, errors="replace")
                except Exception:
                    pass
        # If no plain text part found, derive it from HTML
        if not body and body_html:
            body = _html_to_text(body_html)
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                raw = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    body_html = raw
                    body = _html_to_text(raw)
                else:
                    body = raw
        except Exception:
            body = ""

    snippet = body[:200] if body else ""

    # Check for unsubscribe header
    unsub = msg.get("List-Unsubscribe", "")
    unsub_url = None
    if unsub:
        url_match = re.search(r"<(https?://[^>]+)>", unsub)
        if url_match:
            unsub_url = url_match.group(1)

    return {
        "id": msg_id_str,
        "thread_id": msg.get("In-Reply-To", ""),
        "subject": subject,
        "sender": sender_name or sender_email,
        "sender_email": sender_email,
        "snippet": snippet,
        "body": body[:5000],  # Limit body size (plain text for LLM)
        "body_html": body_html[:50000] if body_html else None,  # Raw HTML for display
        "date": date_str,
        "labels": "[]",
        "unsubscribe_url": unsub_url,
        "processed": 0,
    }


def fetch_unread(max_results: int = 0) -> list:
    """Fetch ALL emails from IMAP inbox (read + unread). 0 = no limit."""
    return fetch_all(max_results=max_results)


def fetch_all(max_results: int = 0) -> list:
    """Fetch emails from IMAP inbox. max_results=0 means ALL emails (no limit)."""
    try:
        imap = _get_connection()
        imap.select("INBOX", readonly=True)

        # Search for ALL messages
        status, messages = imap.search(None, "ALL")
        if status != "OK" or not messages[0]:
            imap.logout()
            return []

        # Get message IDs — 0 means all, otherwise take last N
        msg_ids = messages[0].split()
        if max_results > 0 and len(msg_ids) > max_results:
            recent_ids = msg_ids[-max_results:]
        else:
            recent_ids = msg_ids
        # Reverse so newest first
        recent_ids = list(reversed(recent_ids))

        emails = []
        for msg_id in recent_ids:
            try:
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status == "OK" and msg_data[0]:
                    parsed = _parse_email_message(msg_data, msg_id.decode())
                    emails.append(parsed)
            except Exception as e:
                print(f"  ⚠️  Error parsing message {msg_id}: {e}")
                continue

        imap.logout()
        print(f"  📧 IMAP: Fetched {len(emails)} emails from inbox")
        return emails

    except Exception as e:
        print(f"  ⚠️  Error fetching emails via IMAP: {e}")
        return []


def fetch_recent(max_results: int = 30) -> list:
    """Fetch recent emails (alias for fetch_all)."""
    return fetch_all(max_results=max_results)


def get_email_body(email_id: str) -> str:
    """Get full body of a specific email by IMAP sequence number."""
    try:
        imap = _get_connection()
        imap.select("INBOX", readonly=True)
        status, msg_data = imap.fetch(email_id.encode(), "(RFC822)")
        imap.logout()
        if status == "OK" and msg_data[0]:
            parsed = _parse_email_message(msg_data, email_id)
            return parsed.get("body", "")
        return ""
    except Exception:
        return ""


def mark_read(email_id: str) -> bool:
    """Mark email as read via IMAP."""
    try:
        imap = _get_connection()
        imap.select("INBOX")
        imap.store(email_id.encode(), "+FLAGS", "\\Seen")
        imap.logout()
        return True
    except Exception:
        return False


def trash_email(email_id: str) -> bool:
    """Move email to trash via IMAP."""
    try:
        imap = _get_connection()
        imap.select("INBOX")
        # Try common trash folder names
        for trash_name in ["[Gmail]/Trash", "Trash", "Deleted Messages", "Deleted Items"]:
            try:
                imap.copy(email_id.encode(), trash_name)
                imap.store(email_id.encode(), "+FLAGS", "\\Deleted")
                imap.expunge()
                imap.logout()
                log_action(email_id, "trash", "success")
                return True
            except Exception:
                continue
        # Fallback: just mark as deleted
        imap.store(email_id.encode(), "+FLAGS", "\\Deleted")
        imap.expunge()
        imap.logout()
        log_action(email_id, "trash", "success")
        return True
    except Exception as e:
        log_action(email_id, "trash", "error", str(e))
        return False


def archive_email(email_id: str) -> bool:
    """Archive email via IMAP (move to All Mail or Archive)."""
    try:
        imap = _get_connection()
        imap.select("INBOX")
        # Try common archive folder names
        for archive_name in ["[Gmail]/All Mail", "Archive", "All Mail"]:
            try:
                imap.copy(email_id.encode(), archive_name)
                imap.store(email_id.encode(), "+FLAGS", "\\Deleted")
                imap.expunge()
                imap.logout()
                log_action(email_id, "archive", "success")
                return True
            except Exception:
                continue
        # Fallback: just remove from inbox
        imap.store(email_id.encode(), "+FLAGS", "\\Deleted")
        imap.expunge()
        imap.logout()
        log_action(email_id, "archive", "success")
        return True
    except Exception as e:
        log_action(email_id, "archive", "error", str(e))
        return False


# ── Multi-Account Support ───────────────────────────────────────────

def _get_account_connection(account: dict):
    """Create an authenticated IMAP connection for a specific account."""
    host = account.get("imap_host")
    port = int(account.get("imap_port") or 993)
    username = account.get("imap_user") or account.get("email")
    password = account.get("imap_pass")

    if not all([host, username, password]):
        raise Exception(f"Account {account.get('email')} missing IMAP credentials.")

    imap = imaplib.IMAP4_SSL(host, port)
    imap.login(username, password)
    return imap


def fetch_from_account(account: dict, max_results: int = 0) -> list:
    """Fetch emails from a specific email account. 0 = no limit (all emails)."""
    account_id = account.get("id")
    account_email = account.get("email", "unknown")
    try:
        imap = _get_account_connection(account)
        imap.select("INBOX", readonly=True)

        status, messages = imap.search(None, "ALL")
        if status != "OK" or not messages[0]:
            imap.logout()
            return []

        msg_ids = messages[0].split()
        if max_results > 0 and len(msg_ids) > max_results:
            recent_ids = msg_ids[-max_results:]
        else:
            recent_ids = msg_ids
        recent_ids = list(reversed(recent_ids))

        emails = []
        for msg_id in recent_ids:
            try:
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status == "OK" and msg_data[0]:
                    parsed = _parse_email_message(msg_data, msg_id.decode())
                    # Tag with account info
                    parsed["account_id"] = account_id
                    # Make ID unique across accounts to avoid collisions
                    parsed["id"] = f"acct{account_id}_{parsed['id']}"
                    emails.append(parsed)
            except Exception as e:
                print(f"  ⚠️  Error parsing message {msg_id} from {account_email}: {e}")
                continue

        imap.logout()
        # Update last sync time
        if account_id:
            try:
                update_account_last_sync(account_id)
            except Exception:
                pass
        print(f"  📧 IMAP: Fetched {len(emails)} emails from {account_email}")
        return emails

    except Exception as e:
        print(f"  ⚠️  Error fetching from account {account_email}: {e}")
        return []


def fetch_all_accounts(max_per_account: int = 0) -> list:
    """Fetch emails from all enabled email accounts + the primary IMAP config."""
    all_emails = []

    # 1. Fetch from the primary IMAP config (legacy/setup-wizard account)
    try:
        primary = fetch_all(max_results=max_per_account)
        all_emails.extend(primary)
    except Exception as e:
        print(f"  ⚠️  Primary IMAP fetch failed: {e}")

    # 2. Fetch from all enabled accounts in the email_accounts table
    try:
        accounts = get_email_accounts(enabled_only=True)
    except Exception:
        accounts = []

    for account in accounts:
        try:
            acct_emails = fetch_from_account(account, max_results=max_per_account)
            all_emails.extend(acct_emails)
        except Exception as e:
            print(f"  ⚠️  Account {account.get('email')} fetch failed: {e}")
            continue

    print(f"  📧 IMAP Multi-Account: Total {len(all_emails)} emails from {1 + len(accounts)} source(s)")
    return all_emails
