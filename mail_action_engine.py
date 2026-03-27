#!/usr/bin/env python3
"""
mail_action_engine.py — Decision engine + action executor for macOS Mail
Processes classified emails and routes them to actions via Mail API
Based on gmail-ai-manager but adapted for IMAP + AppleScript
"""

import time
from datetime import datetime
from typing import Optional, Dict, List
from database import (
    get_config, save_email, mark_processed,
    add_action, complete_action, log_action,
    get_emails, get_email
)
from mail_client import create_mail_client, MailMessage
from llm_engine import classify_email, draft_reply
from unsubscribe import safe_unsubscribe

# ── Global mail client ────────────────────────────────────────────────

_mail_client = None


def init_mail_client() -> bool:
    """Initialize mail client from config"""
    global _mail_client
    try:
        config = {
            'imap_host': get_config('mail_imap_host', 'imap.gmail.com'),
            'imap_port': int(get_config('mail_imap_port', '993')),
            'username': get_config('mail_imap_username', ''),
            'password': get_config('mail_imap_password', ''),
            'account_name': get_config('mail_account_name', 'Default Account'),
        }
        
        if not config['username'] or not config['password']:
            print("❌ Mail credentials not configured")
            return False
        
        _mail_client = create_mail_client(config)
        return _mail_client.connect()
    except Exception as e:
        print(f"❌ Mail client initialization failed: {e}")
        return False


def get_mail_client():
    """Get or initialize mail client"""
    global _mail_client
    if _mail_client is None:
        init_mail_client()
    return _mail_client


# ── Config thresholds ─────────────────────────────────────────────────

def _auto_threshold() -> float:
    """Confidence threshold above which actions execute automatically."""
    return float(get_config("auto_threshold", 0.90))


def _auto_archive_spam() -> bool:
    return get_config("auto_archive_spam", "true") == "true"


def _auto_unsubscribe() -> bool:
    return get_config("auto_unsubscribe", "false") == "true"


def _require_approval() -> bool:
    return get_config("require_approval", "true") == "true"


def _rate_limit() -> int:
    """Max auto-actions per run."""
    return int(get_config("rate_limit_per_run", 10))


# ── Mail operations ───────────────────────────────────────────────────

def fetch_unread_mail(max_results: int = 50) -> List[Dict]:
    """
    Fetch unread emails from Mail and convert to uniform dict format
    Returns list compatible with classify_email()
    """
    client = get_mail_client()
    if not client or not client.imap_client.is_connected:
        print("❌ Mail client not connected")
        return []
    
    messages = client.fetch_emails(mailbox="INBOX", limit=max_results)
    
    # Convert MailMessage objects to dict format for compatibility
    emails = []
    for msg in messages:
        if not msg.is_read:  # Only unread
            email_dict = {
                'id': msg.id,
                'sender': msg.sender,
                'sender_email': _extract_email(msg.sender),
                'subject': msg.subject,
                'body': msg.body,
                'date': msg.date.isoformat() if msg.date else None,
                'timestamp': int(msg.date.timestamp()) if msg.date else 0,
                'thread_id': msg.message_id,
                'message_id': msg.message_id,
                'mailbox': msg.mailbox,
                'account': msg.account,
                'raw_message': msg,  # Keep original for later operations
                'unsubscribe_url': _extract_unsubscribe_url(msg),
            }
            emails.append(email_dict)
    
    return emails


def _extract_email(sender_str: str) -> str:
    """Extract email address from sender string"""
    import re
    match = re.search(r'[\w\.-]+@[\w\.-]+', sender_str)
    return match.group(0) if match else sender_str


def _extract_unsubscribe_url(msg: MailMessage) -> Optional[str]:
    """Extract RFC 2369 List-Unsubscribe URL from email headers"""
    # This would require access to raw headers - implement if needed
    # For now, return None to indicate not available
    return None


def archive_mail(email: Dict) -> bool:
    """Archive email in Mail"""
    client = get_mail_client()
    if not client or not email.get('raw_message'):
        return False
    
    try:
        mail_msg = email['raw_message']
        result = client.archive_email(mail_msg)
        if result:
            print(f"✅ Archived: {email['subject'][:50]}")
        return result
    except Exception as e:
        print(f"❌ Archive failed: {e}")
        return False


def trash_mail(email: Dict) -> bool:
    """Move email to spam/trash in Mail"""
    client = get_mail_client()
    if not client or not email.get('raw_message'):
        return False
    
    try:
        mail_msg = email['raw_message']
        result = client.move_to_spam(mail_msg)
        if result:
            print(f"✅ Moved to spam: {email['subject'][:50]}")
        return result
    except Exception as e:
        print(f"❌ Trash failed: {e}")
        return False


def mark_read_mail(email: Dict) -> bool:
    """Mark email as read in Mail"""
    client = get_mail_client()
    if not client or not email.get('raw_message'):
        return False
    
    try:
        mail_msg = email['raw_message']
        result = client.mark_read(mail_msg)
        return result
    except Exception as e:
        print(f"❌ Mark read failed: {e}")
        return False


def flag_mail(email: Dict) -> bool:
    """Flag email in Mail"""
    client = get_mail_client()
    if not client or not email.get('raw_message'):
        return False
    
    try:
        mail_msg = email['raw_message']
        result = client.flag_email(mail_msg, True)
        return result
    except Exception as e:
        print(f"❌ Flag failed: {e}")
        return False


# ── Main pipeline ─────────────────────────────────────────────────────

def run_pipeline(max_emails: int = 30) -> dict:
    """
    Full pipeline:
    1. Fetch unread emails from Mail
    2. Classify each with LLM
    3. Apply auto-actions or queue for approval
    Returns stats dict.
    """
    stats = {
        "fetched": 0,
        "classified": 0,
        "auto_archived": 0,
        "auto_trashed": 0,
        "auto_unsubscribed": 0,
        "queued_for_approval": 0,
        "errors": 0,
        "started_at": datetime.now().isoformat(),
    }

    print(f"\n{'='*60}")
    print(f"  📬 Mail AI Manager — Pipeline Run")
    print(f"{'='*60}\n")

    # Step 1: Fetch
    try:
        emails = fetch_unread_mail(max_results=max_emails)
        stats["fetched"] = len(emails)
        print(f"📥 Fetched {len(emails)} unread emails from Mail")
    except Exception as e:
        print(f"❌ Fetch error: {e}")
        stats["errors"] += 1
        return stats

    auto_actions = 0
    threshold    = _auto_threshold()

    for email in emails:
        try:
            # Step 2: Classify
            print(f"\n  ✉️  [{email.get('sender_email', '?')}] {email.get('subject', '?')[:50]}")
            classification = classify_email(email)

            # Merge classification into email dict
            email.update({
                "category":   classification["category"],
                "confidence": classification["confidence"],
                "llm_action": classification["action"],
            })

            # Generate draft reply if needed
            if classification.get("needs_reply") and classification["category"] in ("work", "personal", "urgent"):
                print(f"     📝 Drafting reply...")
                reply = draft_reply(email)
                email["draft_reply"] = reply
            else:
                email["draft_reply"] = None

            # Save to DB
            save_email(email)
            stats["classified"] += 1

            print(f"     🏷️  {classification['category']} ({classification['confidence']:.0%}) → {classification['action']}")

            # Step 3: Route action
            action = classification["action"]
            confidence = classification["confidence"]
            auto_ok = (confidence >= threshold) and (auto_actions < _rate_limit())

            if action == "trash" and _auto_archive_spam() and auto_ok:
                # High-confidence spam → auto-trash
                success = trash_mail(email)
                mark_read_mail(email)
                mark_processed(email["id"])
                if success:
                    auto_actions += 1
                    stats["auto_trashed"] += 1
                    print(f"     🗑️  Auto-trashed (spam)")
                else:
                    _queue_action(email["id"], "trash", f"Auto-trash failed, manual review")

            elif action == "archive" and auto_ok and not _require_approval():
                success = archive_mail(email)
                mark_read_mail(email)
                mark_processed(email["id"])
                if success:
                    auto_actions += 1
                    stats["auto_archived"] += 1
                    print(f"     📦 Auto-archived")
                else:
                    _queue_action(email["id"], "archive", "Auto-archive failed")

            elif action == "unsubscribe" and _auto_unsubscribe() and email.get("unsubscribe_url"):
                result = safe_unsubscribe(email["unsubscribe_url"], email["sender_email"])
                mark_processed(email["id"])
                auto_actions += 1
                stats["auto_unsubscribed"] += 1
                print(f"     🚫 Unsubscribed from {email.get('sender_email')}")

            else:
                # Queue for approval
                notes = classification.get("reason", "")
                if email.get("draft_reply"):
                    notes += f" | Draft ready"
                _queue_action(email["id"], action, notes)
                stats["queued_for_approval"] += 1
                print(f"     ⏳ Queued for approval")

        except Exception as e:
            print(f"  ⚠️  Error processing email {email.get('id')}: {e}")
            stats["errors"] += 1

    stats["completed_at"] = datetime.now().isoformat()
    print(f"\n{'='*60}")
    print(f"  ✅ Pipeline complete!")
    print(f"     Classified: {stats['classified']}")
    print(f"     Auto-trashed: {stats['auto_trashed']}")
    print(f"     Auto-archived: {stats['auto_archived']}")
    print(f"     Queued: {stats['queued_for_approval']}")
    print(f"{'='*60}\n")

    return stats


def _queue_action(email_id: str, action_type: str, notes: str = ""):
    """Add action to approval queue."""
    add_action(email_id, action_type, notes)


# ── Individual action executors ───────────────────────────────────────

def execute_action(action_id: int, action_type: str, email_id: str,
                   custom_body: str = None) -> dict:
    """
    Execute a specific action (called from approval UI).
    Returns {"success": bool, "message": str}
    """
    try:
        email = get_email(email_id)
        if not email:
            return {"success": False, "message": "Email not found"}

        if action_type == "archive":
            ok = archive_mail(email)
            mark_read_mail(email)

        elif action_type == "trash":
            ok = trash_mail(email)

        elif action_type in ("label", "flag"):
            ok = flag_mail(email)

        elif action_type == "unsubscribe":
            if email and email.get("unsubscribe_url"):
                result = safe_unsubscribe(
                    email["unsubscribe_url"],
                    email.get("sender_email", "")
                )
                ok = result.get("success", False)
                archive_mail(email)
            else:
                ok = False

        elif action_type == "draft_reply":
            # For Mail, we just save the draft - no direct draft creation API like Gmail
            ok = True
            print(f"📝 Draft ready in approval queue: {email.get('subject', '')[:50]}")

        elif action_type == "send_reply":
            # Note: Sending from Mail requires different approach
            # This would typically open Mail compose or use AppleScript
            ok = False  # Not yet implemented
            print(f"⚠️  Send reply not yet implemented for Mail")

        elif action_type == "skip":
            ok = True

        else:
            ok = False

        if ok:
            complete_action(action_id, "done")
            mark_processed(email_id)
            log_action(email_id, action_type, "success")
            return {"success": True, "message": f"{action_type} completed"}
        else:
            complete_action(action_id, "failed")
            return {"success": False, "message": f"{action_type} failed"}

    except Exception as e:
        complete_action(action_id, "error")
        log_action(email_id, action_type, "error", str(e))
        return {"success": False, "message": str(e)}


def bulk_execute(action_ids: list, action_type: str) -> dict:
    """Execute multiple actions at once."""
    results = {"success": 0, "failed": 0}
    from database import get_pending_actions
    pending = {a["id"]: a for a in get_pending_actions(1000)}
    for aid in action_ids:
        action = pending.get(aid)
        if action:
            result = execute_action(
                aid, action_type or action["action_type"], action["email_id"]
            )
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
    return results
