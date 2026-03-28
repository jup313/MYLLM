#!/usr/bin/env python3
"""
action_engine.py — Decision engine + action executor
Processes classified emails and routes them to actions.

Pipeline v2: Fetch ALL → Save ALL to DB → Classify → Route actions
- Batch IMAP fetch (50x faster)
- Dedup: skip emails already in database
- Save before classify: nothing lost if LLM crashes
- Granular progress reporting for UI
"""

import time
from datetime import datetime
from database import (
    get_config, save_email, mark_processed,
    add_action, complete_action, log_action,
    get_emails
)

# ── Shared progress state (read by app.py /api/pipeline/status) ─────
pipeline_progress = {
    "phase": "idle",          # idle | fetching | saving | classifying | done | error
    "fetch_checked": 0,       # emails checked from IMAP so far
    "fetch_total": 0,         # total emails on server
    "fetch_downloaded": 0,    # emails actually downloaded
    "save_done": 0,           # emails saved to DB (after dedup)
    "save_total": 0,          # total new emails to save
    "save_skipped": 0,        # emails skipped (already in DB)
    "classify_done": 0,       # emails classified by LLM
    "classify_total": 0,      # total emails to classify
    "message": "",            # human-readable status message
}

def _reset_progress():
    global pipeline_progress
    pipeline_progress = {
        "phase": "idle", "fetch_checked": 0, "fetch_total": 0,
        "fetch_downloaded": 0, "save_done": 0, "save_total": 0,
        "save_skipped": 0, "classify_done": 0, "classify_total": 0,
        "message": "",
    }


# ── Dynamic mail client import ──────────────────────────────────────

def _get_mail_client():
    """Return the appropriate mail client module based on config."""
    from database import get_config as _gc
    mode = _gc("mail_mode") or "imap"
    if mode == "imap":
        import imap_client
        return imap_client
    elif mode == "macos_mail":
        import macos_mail
        return macos_mail
    else:
        try:
            import imap_client
            return imap_client
        except ImportError:
            import gmail_client
            return gmail_client

def fetch_unread(max_results=0, progress_callback=None):
    return _get_mail_client().fetch_unread(max_results=max_results, progress_callback=progress_callback)

def archive_email(email_id):
    return _get_mail_client().archive_email(email_id)

def trash_email(email_id):
    return _get_mail_client().trash_email(email_id)

def mark_read(email_id):
    return _get_mail_client().mark_read(email_id)

def apply_label(email_id, label="AI-Reviewed"):
    """Apply label — only supported by Gmail client, otherwise mark read."""
    client = _get_mail_client()
    if hasattr(client, 'apply_label'):
        return client.apply_label(email_id, label)
    return mark_read(email_id)  # fallback

def create_draft(to, subject, body, thread_id=None):
    """Create draft — only supported by Gmail client."""
    client = _get_mail_client()
    if hasattr(client, 'create_draft'):
        return client.create_draft(to, subject, body, thread_id)
    return {"success": False, "error": "Drafts not supported in current mail mode"}

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


# ── Get existing email IDs from DB (for dedup) ──────────────────────

def _get_existing_email_ids() -> set:
    """Return a set of all email IDs already saved in the database."""
    from database import get_conn
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM emails")
    ids = set(row[0] for row in c.fetchall())
    conn.close()
    return ids


# ── Main pipeline v2 ─────────────────────────────────────────────────

def run_pipeline(max_emails: int = 0) -> dict:
    """
    Full pipeline v2 — optimized for thousands of emails:
    
    Phase 1: FETCH — Batch-download all emails from IMAP (50x faster)
    Phase 2: SAVE  — Deduplicate & save all new emails to DB (nothing lost)
    Phase 3: CLASSIFY — LLM classifies only unclassified emails
    Phase 4: ROUTE — Apply auto-actions or queue for approval
    
    Returns stats dict.
    """
    global pipeline_progress
    _reset_progress()

    stats = {
        "fetched": 0,
        "new_emails": 0,
        "skipped_existing": 0,
        "classified": 0,
        "auto_archived": 0,
        "auto_trashed": 0,
        "auto_unsubscribed": 0,
        "queued_for_approval": 0,
        "errors": 0,
        "started_at": datetime.now().isoformat(),
    }

    print(f"\n{'='*60}")
    print(f"  📬 Mail AI Manager — Pipeline Run v2 (Batch Mode)")
    print(f"{'='*60}\n")

    # ── Phase 1: FETCH all emails from IMAP ─────────────────────────
    pipeline_progress["phase"] = "fetching"
    pipeline_progress["message"] = "Connecting to email server..."

    def fetch_progress(checked, total, downloaded, *args):
        pipeline_progress["fetch_checked"] = checked
        pipeline_progress["fetch_total"] = total
        pipeline_progress["fetch_downloaded"] = downloaded
        pct = round(checked / total * 100) if total > 0 else 0
        pipeline_progress["message"] = f"Fetching emails: {downloaded:,} downloaded ({checked:,}/{total:,} checked, {pct}%)"

    try:
        client = _get_mail_client()
        if hasattr(client, 'fetch_all_accounts'):
            emails = client.fetch_all_accounts(max_per_account=max_emails, progress_callback=fetch_progress)
        else:
            emails = fetch_unread(max_results=max_emails, progress_callback=fetch_progress)
        stats["fetched"] = len(emails)
        print(f"\n📥 Phase 1 complete: Fetched {len(emails):,} emails from server")
    except Exception as e:
        print(f"❌ Fetch error: {e}")
        pipeline_progress["phase"] = "error"
        pipeline_progress["message"] = f"Fetch error: {e}"
        stats["errors"] += 1
        return stats

    if not emails:
        pipeline_progress["phase"] = "done"
        pipeline_progress["message"] = "No emails found on server"
        stats["completed_at"] = datetime.now().isoformat()
        return stats

    # ── Phase 2: SAVE all new emails to DB (dedup) ──────────────────
    pipeline_progress["phase"] = "saving"
    pipeline_progress["message"] = "Checking for new emails..."

    existing_ids = _get_existing_email_ids()
    new_emails = []
    skipped = 0

    for em in emails:
        if em.get("id") and str(em["id"]) in existing_ids:
            skipped += 1
        else:
            new_emails.append(em)

    stats["skipped_existing"] = skipped
    stats["new_emails"] = len(new_emails)
    pipeline_progress["save_total"] = len(new_emails)
    pipeline_progress["save_skipped"] = skipped

    print(f"📋 Phase 2: {len(new_emails):,} new emails to save ({skipped:,} already in DB)")

    # Save all new emails to DB WITHOUT classification (fast — no LLM needed)
    saved_count = 0
    for em in new_emails:
        try:
            # Save with minimal fields — classification comes later
            if "category" not in em:
                em["category"] = None
            if "confidence" not in em:
                em["confidence"] = None
            if "llm_action" not in em:
                em["llm_action"] = None
            if "importance" not in em:
                em["importance"] = None
            if "importance_reason" not in em:
                em["importance_reason"] = None
            if "draft_reply" not in em:
                em["draft_reply"] = None

            save_email(em)
            saved_count += 1
            pipeline_progress["save_done"] = saved_count
            if saved_count % 100 == 0 or saved_count == len(new_emails):
                pipeline_progress["message"] = f"Saved {saved_count:,}/{len(new_emails):,} new emails to database ({skipped:,} skipped)"
                print(f"  💾 Saved {saved_count:,}/{len(new_emails):,}")
        except Exception as e:
            # Duplicate or other error — just skip
            stats["errors"] += 1

    print(f"💾 Phase 2 complete: Saved {saved_count:,} new emails")

    # ── Phase 3: CLASSIFY unclassified emails ───────────────────────
    pipeline_progress["phase"] = "classifying"

    # Get all unclassified emails from DB (includes newly saved + any from previous runs)
    from database import get_conn
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, subject, sender, sender_email, body, snippet, date, unsubscribe_url, body_html, starred FROM emails WHERE category IS NULL OR category = '' ORDER BY rowid DESC")
    rows = c.fetchall()
    conn.close()

    unclassified = []
    for row in rows:
        unclassified.append({
            "id": row[0], "subject": row[1], "sender": row[2],
            "sender_email": row[3], "body": row[4], "snippet": row[5],
            "date": row[6], "unsubscribe_url": row[7], "body_html": row[8],
            "starred": row[9],
        })

    pipeline_progress["classify_total"] = len(unclassified)
    pipeline_progress["message"] = f"Classifying {len(unclassified):,} emails with AI..."
    print(f"🧠 Phase 3: Classifying {len(unclassified):,} unclassified emails")

    auto_actions = 0
    threshold    = _auto_threshold()

    for i, em in enumerate(unclassified):
        try:
            # Classify with LLM
            classification = classify_email(em)

            # Merge classification
            em.update({
                "category":   classification["category"],
                "confidence": classification["confidence"],
                "llm_action": classification["action"],
                "importance": classification.get("importance", "not_important"),
                "importance_reason": classification.get("importance_reason", ""),
            })

            # Generate draft reply if needed
            if classification.get("needs_reply") and classification["category"] in ("work", "personal", "urgent"):
                reply = draft_reply(em)
                em["draft_reply"] = reply
            else:
                em["draft_reply"] = None

            # Update email in DB with classification
            save_email(em)
            stats["classified"] += 1
            pipeline_progress["classify_done"] = stats["classified"]
            pipeline_progress["message"] = f"Classified {stats['classified']:,}/{len(unclassified):,} emails — {classification['category']} ({classification['confidence']:.0%})"

            if stats["classified"] % 10 == 0 or stats["classified"] == len(unclassified):
                print(f"  🧠 Classified {stats['classified']:,}/{len(unclassified):,}")

            # ── Phase 4: Route action ────────────────────────────────
            action = classification["action"]
            confidence = classification["confidence"]
            auto_ok = (confidence >= threshold) and (auto_actions < _rate_limit())
            approval_required = _require_approval()

            if action == "trash" and auto_ok:
                success = trash_email(em["id"])
                mark_read(em["id"])
                mark_processed(em["id"])
                log_action(em["id"], "auto_trash", "success", f"AI: {classification.get('reason','')}")
                if success:
                    auto_actions += 1
                    stats["auto_trashed"] += 1
                else:
                    _queue_action(em["id"], "trash", "Auto-trash failed")

            elif action == "archive" and auto_ok:
                success = archive_email(em["id"])
                mark_read(em["id"])
                mark_processed(em["id"])
                log_action(em["id"], "auto_archive", "success", f"AI: {classification.get('reason','')}")
                if success:
                    auto_actions += 1
                    stats["auto_archived"] += 1
                else:
                    _queue_action(em["id"], "archive", "Auto-archive failed")

            elif action == "unsubscribe" and em.get("unsubscribe_url"):
                result = safe_unsubscribe(em["unsubscribe_url"], em["sender_email"])
                archive_email(em["id"])
                mark_read(em["id"])
                mark_processed(em["id"])
                log_action(em["id"], "auto_unsubscribe", "success", f"Unsubscribed from {em.get('sender_email')}")
                auto_actions += 1
                stats["auto_unsubscribed"] += 1

            elif action in ("label", "flag") and auto_ok:
                apply_label(em["id"], "AI-Reviewed")
                mark_read(em["id"])
                mark_processed(em["id"])
                log_action(em["id"], "auto_label", "success", f"AI: {classification.get('reason','')}")
                auto_actions += 1
                stats["auto_archived"] += 1

            elif action == "draft_reply" and classification.get("needs_reply") and em.get("draft_reply"):
                if not approval_required:
                    create_draft(em.get("sender_email",""), f"Re: {em.get('subject','')}", em["draft_reply"], em.get("thread_id"))
                    mark_processed(em["id"])
                    log_action(em["id"], "auto_draft", "success", "AI draft reply created")
                    auto_actions += 1
                else:
                    _queue_action(em["id"], action, classification.get("reason", "") + " | Draft ready")
                    stats["queued_for_approval"] += 1

            elif not auto_ok and approval_required:
                notes = classification.get("reason", "")
                if em.get("draft_reply"):
                    notes += " | Draft ready"
                _queue_action(em["id"], action, notes)
                stats["queued_for_approval"] += 1

            else:
                if not approval_required and auto_ok:
                    if action in ("trash",):
                        trash_email(em["id"])
                    else:
                        archive_email(em["id"])
                    mark_read(em["id"])
                    mark_processed(em["id"])
                    log_action(em["id"], f"auto_{action}", "success", f"AI fallback: {classification.get('reason','')}")
                    auto_actions += 1
                    stats["auto_archived"] += 1
                else:
                    _queue_action(em["id"], action, classification.get("reason", ""))
                    stats["queued_for_approval"] += 1

        except Exception as e:
            print(f"  ⚠️  Error processing email {em.get('id')}: {e}")
            stats["errors"] += 1

    # ── Done ─────────────────────────────────────────────────────────
    stats["completed_at"] = datetime.now().isoformat()
    pipeline_progress["phase"] = "done"
    pipeline_progress["message"] = f"Pipeline complete! {stats['fetched']:,} fetched, {stats['new_emails']:,} new, {stats['classified']:,} classified"

    print(f"\n{'='*60}")
    print(f"  ✅ Pipeline v2 complete!")
    print(f"     Fetched from server:  {stats['fetched']:,}")
    print(f"     Already in DB:        {stats['skipped_existing']:,}")
    print(f"     New emails saved:     {stats['new_emails']:,}")
    print(f"     Classified by AI:     {stats['classified']:,}")
    print(f"     Auto-trashed:         {stats['auto_trashed']:,}")
    print(f"     Auto-archived:        {stats['auto_archived']:,}")
    print(f"     Queued for review:    {stats['queued_for_approval']:,}")
    print(f"     Errors:               {stats['errors']:,}")
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
            email = get_email(email_id)
            if email and custom_body:
                subject = f"Re: {email.get('subject', '')}"
                to      = email.get("sender_email", "")
                client = _get_mail_client()
                if hasattr(client, 'send_email'):
                    result = client.send_email(to, subject, custom_body, email.get("thread_id"))
                    ok = result.get("success", False)
                else:
                    ok = False
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
