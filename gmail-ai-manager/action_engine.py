#!/usr/bin/env python3
"""
action_engine.py — Decision engine + action executor
Processes classified emails and routes them to actions.
"""

import time
from datetime import datetime
from database import (
    get_config, save_email, mark_processed,
    add_action, complete_action, log_action,
    get_emails
)
from gmail_client import (
    fetch_unread, archive_email, trash_email,
    apply_label, create_draft, mark_read
)
from llm_engine import classify_email, draft_reply
from unsubscribe import safe_unsubscribe

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


# ── Main pipeline ─────────────────────────────────────────────────────

def run_pipeline(max_emails: int = 30) -> dict:
    """
    Full pipeline:
    1. Fetch unread emails from Gmail
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
    print(f"  📬 Gmail AI Manager — Pipeline Run")
    print(f"{'='*60}\n")

    # Step 1: Fetch
    try:
        emails = fetch_unread(max_results=max_emails)
        stats["fetched"] = len(emails)
        print(f"📥 Fetched {len(emails)} unread emails")
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
                success = trash_email(email["id"])
                mark_read(email["id"])
                mark_processed(email["id"])
                if success:
                    auto_actions += 1
                    stats["auto_trashed"] += 1
                    print(f"     🗑️  Auto-trashed (spam)")
                else:
                    _queue_action(email["id"], "trash", f"Auto-trash failed, manual review")

            elif action == "archive" and auto_ok and not _require_approval():
                success = archive_email(email["id"])
                mark_read(email["id"])
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
        if action_type == "archive":
            ok = archive_email(email_id)
            mark_read(email_id)

        elif action_type == "trash":
            ok = trash_email(email_id)

        elif action_type in ("label", "flag"):
            ok = apply_label(email_id, "AI-Reviewed")

        elif action_type == "unsubscribe":
            from database import get_email
            email = get_email(email_id)
            if email and email.get("unsubscribe_url"):
                result = safe_unsubscribe(
                    email["unsubscribe_url"],
                    email.get("sender_email", "")
                )
                ok = result.get("success", False)
                archive_email(email_id)
            else:
                ok = False

        elif action_type == "draft_reply":
            from database import get_email
            from gmail_client import create_draft
            email = get_email(email_id)
            if email:
                body    = custom_body or email.get("draft_reply", "")
                subject = f"Re: {email.get('subject', '')}"
                to      = email.get("sender_email", "")
                result  = create_draft(to, subject, body, email.get("thread_id"))
                ok      = result.get("success", False)
            else:
                ok = False

        elif action_type == "send_reply":
            from database import get_email
            from gmail_client import send_email
            email = get_email(email_id)
            if email and custom_body:
                subject = f"Re: {email.get('subject', '')}"
                to      = email.get("sender_email", "")
                result  = send_email(to, subject, custom_body, email.get("thread_id"))
                ok      = result.get("success", False)
            else:
                ok = False

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
    from database import get_pending_actions, get_email
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
