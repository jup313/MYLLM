#!/usr/bin/env python3
"""
llm_engine.py — Ollama LLM classifier + reply drafter
Classifies emails and generates draft replies.
"""

import json
import re
import requests
from database import get_config

CATEGORIES = ["spam", "marketing", "personal", "work", "urgent", "notification"]

CLASSIFY_PROMPT = """You are an email classifier. Analyze the email and return ONLY valid JSON.

Email:
Subject: {subject}
From: {sender} <{sender_email}>
Body: {body}

Return ONLY this JSON (no markdown, no explanation):
{{
  "category": "spam|marketing|personal|work|urgent|notification",
  "confidence": 0.0-1.0,
  "action": "archive|label|trash|draft_reply|unsubscribe|flag",
  "priority": "low|medium|high",
  "reason": "one sentence explanation",
  "is_bulk_sender": true|false,
  "needs_reply": true|false
}}"""

DRAFT_PROMPT = """You are a professional email assistant. Write a concise, polite reply.

Original email:
Subject: {subject}
From: {sender}
Body: {body}

Write ONLY the reply body text (no subject line, no "Subject:", no explanation).
Keep it professional, brief, and friendly. 2-4 sentences max."""


def _get_ollama_url() -> str:
    return get_config("ollama_url", "http://localhost:11434")


def _get_model() -> str:
    return get_config("ollama_model", "mistral:7b")


def _call_ollama(prompt: str, system: str = None, timeout: int = 60) -> str:
    """Call Ollama API and return response text."""
    url   = _get_ollama_url() + "/api/chat"
    model = _get_model()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 300,
        }
    }

    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Cannot connect to Ollama at {url}. Is it running?")
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")


def check_ollama() -> dict:
    """Check if Ollama is running and return available models."""
    url = _get_ollama_url()
    try:
        r = requests.get(url + "/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        return {"running": True, "models": models}
    except Exception as e:
        return {"running": False, "models": [], "error": str(e)}


def classify_email(email: dict) -> dict:
    """
    Classify an email using the LLM.
    Returns: {category, confidence, action, priority, reason, is_bulk_sender, needs_reply}
    """
    subject      = email.get("subject", "")
    sender       = email.get("sender", "")
    sender_email = email.get("sender_email", "")
    body         = email.get("body", email.get("snippet", ""))[:1500]

    # Quick heuristics first (fast path, no LLM needed)
    heuristic = _heuristic_classify(email)
    if heuristic and heuristic.get("confidence", 0) >= 0.95:
        return heuristic

    prompt = CLASSIFY_PROMPT.format(
        subject=subject,
        sender=sender,
        sender_email=sender_email,
        body=body
    )

    try:
        response = _call_ollama(prompt, timeout=45)
        # Extract JSON from response
        result = _parse_json_response(response)
        if result:
            # Sanitize
            result["category"]   = result.get("category", "notification").lower()
            result["confidence"] = float(result.get("confidence", 0.7))
            result["action"]     = result.get("action", "label").lower()
            result["priority"]   = result.get("priority", "low").lower()
            result["reason"]     = result.get("reason", "")
            result["is_bulk_sender"] = bool(result.get("is_bulk_sender", False))
            result["needs_reply"]    = bool(result.get("needs_reply", False))
            # Override: if unsubscribe URL exists, flag for unsubscribe
            if email.get("unsubscribe_url") and result["category"] == "marketing":
                result["action"] = "unsubscribe"
            return result
    except Exception as e:
        print(f"  ⚠️  LLM classify error: {e}")

    # Fallback
    return {
        "category": "notification",
        "confidence": 0.5,
        "action": "label",
        "priority": "low",
        "reason": "LLM unavailable — manual review",
        "is_bulk_sender": False,
        "needs_reply": False,
    }


def draft_reply(email: dict) -> str:
    """Generate a draft reply for an email using the LLM."""
    subject = email.get("subject", "")
    sender  = email.get("sender", "")
    body    = email.get("body", email.get("snippet", ""))[:1500]

    prompt = DRAFT_PROMPT.format(
        subject=subject,
        sender=sender,
        body=body
    )

    try:
        response = _call_ollama(prompt, timeout=60)
        return response.strip()
    except Exception as e:
        return f"[Draft generation failed: {e}]"


def generate_summary_text(emails: list, period: str = "daily") -> str:
    """Generate a natural language summary of emails."""
    if not emails:
        return "No emails to summarize."

    # Build a compact list for the LLM
    email_list = ""
    for e in emails[:30]:  # Limit to 30 for context
        email_list += f"- [{e.get('category','?')}] From: {e.get('sender','?')} | Subject: {e.get('subject','?')}\n"

    prompt = f"""Summarize these emails in a {period} report. Be concise and highlight priorities.

Emails ({len(emails)} total):
{email_list}

Write a brief executive summary (3-5 sentences) noting:
1. Total count and categories
2. Any urgent/important items
3. What can be ignored
Keep it under 150 words."""

    try:
        return _call_ollama(prompt, timeout=60)
    except Exception as e:
        return f"Summary unavailable: {e}"


# ── Heuristics (fast path) ────────────────────────────────────────────

SPAM_KEYWORDS = [
    "winner", "lottery", "prize", "claim your", "click here to claim",
    "you have been selected", "congratulations you won", "free money",
    "nigerian prince", "bank transfer", "urgent help needed",
    "make money fast", "work from home earn", "bitcoin investment guarantee"
]

MARKETING_KEYWORDS = [
    "unsubscribe", "opt out", "email preferences", "promotional",
    "sale ends", "limited time offer", "% off", "shop now",
    "view in browser", "update your preferences", "newsletter",
    "no-reply@", "noreply@", "marketing@", "offers@", "deals@"
]


def _heuristic_classify(email: dict) -> dict | None:
    """Fast heuristic classification without LLM."""
    subject      = (email.get("subject", "") or "").lower()
    body         = (email.get("body", "") or email.get("snippet", "") or "").lower()
    sender_email = (email.get("sender_email", "") or "").lower()
    has_unsub    = bool(email.get("unsubscribe_url"))
    combined     = subject + " " + body + " " + sender_email

    # Spam detection
    spam_hits = sum(1 for kw in SPAM_KEYWORDS if kw in combined)
    if spam_hits >= 2:
        return {
            "category": "spam",
            "confidence": 0.96,
            "action": "trash",
            "priority": "low",
            "reason": f"Matches {spam_hits} spam keywords",
            "is_bulk_sender": True,
            "needs_reply": False,
        }

    # Marketing detection
    marketing_hits = sum(1 for kw in MARKETING_KEYWORDS if kw in combined)
    if marketing_hits >= 2 or has_unsub:
        action = "unsubscribe" if has_unsub else "archive"
        return {
            "category": "marketing",
            "confidence": 0.92,
            "action": action,
            "priority": "low",
            "reason": f"Marketing email ({marketing_hits} signals, unsub={'yes' if has_unsub else 'no'})",
            "is_bulk_sender": True,
            "needs_reply": False,
        }

    return None


def _parse_json_response(text: str) -> dict | None:
    """Extract JSON object from LLM response."""
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try extracting JSON block
    match = re.search(r"\{[^{}]+\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return None
