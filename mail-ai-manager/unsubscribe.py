#!/usr/bin/env python3
"""
unsubscribe.py — Safe unsubscribe handler
Only uses RFC 2369 List-Unsubscribe headers. Never clicks body links.
"""

import re
import requests
from database import log_action

# Trusted domains that commonly send List-Unsubscribe headers
# (for extra safety validation)
SAFE_UNSUBSCRIBE_PATTERNS = [
    r"unsubscribe\.", r"email\.", r"mail\.", r"list\.",
    r"click\.", r"link\.", r"go\.", r"manage\.",
    r"preferences\.", r"opt-out\.", r"optout\."
]

# Dangerous patterns to block
BLOCK_PATTERNS = [
    r"\.onion", r"127\.0\.0\.1", r"localhost",
    r"192\.168\.", r"10\.\d+\.\d+\.", r"172\.(1[6-9]|2\d|3[0-1])\.",
    r"javascript:", r"data:", r"file://",
    r"phishing", r"malware"
]


def _is_safe_url(url: str) -> bool:
    """Basic safety check for unsubscribe URLs."""
    if not url or not url.startswith("http"):
        return False

    url_lower = url.lower()

    # Block dangerous patterns
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, url_lower):
            return False

    # Must be a proper HTTPS or HTTP URL
    if not re.match(r"https?://[a-zA-Z0-9.-]+/", url):
        return False

    return True


def safe_unsubscribe(unsubscribe_url: str, sender_email: str = "") -> dict:
    """
    Safely unsubscribe from a mailing list.
    Only processes RFC 2369 List-Unsubscribe URLs.
    
    Returns: {"success": bool, "method": str, "message": str}
    """
    if not unsubscribe_url:
        return {"success": False, "method": "none", "message": "No unsubscribe URL provided"}

    # Handle mailto: unsubscribe
    if unsubscribe_url.startswith("mailto:"):
        return _handle_mailto_unsubscribe(unsubscribe_url, sender_email)

    # Handle HTTP/HTTPS unsubscribe
    if unsubscribe_url.startswith("http"):
        return _handle_http_unsubscribe(unsubscribe_url, sender_email)

    return {"success": False, "method": "none", "message": f"Unknown URL scheme: {unsubscribe_url[:50]}"}


def _handle_http_unsubscribe(url: str, sender_email: str) -> dict:
    """Send GET request to unsubscribe URL."""
    if not _is_safe_url(url):
        msg = f"Blocked unsafe URL: {url[:80]}"
        log_action(sender_email, "unsubscribe_blocked", "blocked", msg)
        return {"success": False, "method": "http_blocked", "message": msg}

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        response = requests.get(
            url, 
            headers=headers, 
            timeout=15, 
            allow_redirects=True,
            verify=True  # Always verify SSL
        )
        
        # Check for success indicators in response
        success = response.status_code in (200, 204)
        body_lower = response.text.lower()
        confirmed = any(word in body_lower for word in [
            "unsubscribed", "removed", "opted out", "success",
            "you have been removed", "no longer receive"
        ])

        msg = f"HTTP {response.status_code} — {'confirmed' if confirmed else 'sent'}"
        log_action(sender_email, "unsubscribe_http", "success" if success else "uncertain", msg)

        return {
            "success": success,
            "method": "http_get",
            "message": msg,
            "confirmed": confirmed,
            "url": url
        }

    except requests.exceptions.SSLError:
        log_action(sender_email, "unsubscribe_http", "ssl_error", url[:80])
        return {"success": False, "method": "http_ssl_error", "message": "SSL error — URL may be unsafe"}
    except requests.exceptions.Timeout:
        return {"success": False, "method": "http_timeout", "message": "Request timed out"}
    except Exception as e:
        log_action(sender_email, "unsubscribe_http", "error", str(e))
        return {"success": False, "method": "http_error", "message": str(e)}


def _handle_mailto_unsubscribe(mailto_url: str, sender_email: str) -> dict:
    """
    For mailto: unsubscribe, we note it but don't auto-send emails.
    Instead, we return the info so the UI can show it to the user.
    """
    # Parse: mailto:unsubscribe@example.com?subject=Unsubscribe
    match = re.match(r"mailto:([^?]+)(\?.*)?", mailto_url)
    if not match:
        return {"success": False, "method": "mailto_parse_error", "message": "Invalid mailto URL"}

    to_address = match.group(1)
    params     = match.group(2) or ""
    subject    = "Unsubscribe"
    
    subject_match = re.search(r"[?&]subject=([^&]+)", params)
    if subject_match:
        subject = requests.utils.unquote(subject_match.group(1))

    log_action(sender_email, "unsubscribe_mailto", "noted",
               f"to={to_address} subject={subject}")

    return {
        "success": True,
        "method": "mailto",
        "message": f"Mailto unsubscribe noted: {to_address}",
        "to": to_address,
        "subject": subject,
        "note": "Send an email to unsubscribe manually"
    }


def extract_unsubscribe_from_body(body: str) -> str | None:
    """
    Extract unsubscribe URL from email body as a LAST RESORT.
    Returns None if not found or looks unsafe.
    NOTE: This is informational only — never auto-click body links.
    """
    patterns = [
        r"https?://[^\s<>\"']+unsubscribe[^\s<>\"']*",
        r"https?://[^\s<>\"']+opt.?out[^\s<>\"']*",
        r"https?://[^\s<>\"']+remove[^\s<>\"']*",
    ]
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            url = match.group(0).rstrip(".,;)")
            if _is_safe_url(url):
                return url
    return None
