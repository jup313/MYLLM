"""
calendar_engine.py — Google Calendar integration for Gmail AI Manager
Detects meeting/appointment language in emails and creates calendar events.
Uses the same OAuth credentials already set up for Gmail.
"""

import os
import re
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR   = Path(__file__).parent
TOKEN_PATH = BASE_DIR / "token.json"

# Calendar API scope (add to Gmail OAuth if re-authorizing)
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"

# ── Auth ───────────────────────────────────────────────────────────────────────

def get_calendar_service():
    """Build Google Calendar API service using existing token."""
    if not TOKEN_PATH.exists():
        raise RuntimeError("Not authenticated. Complete Gmail OAuth first.")

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def is_calendar_authorized() -> bool:
    """Check if calendar scope is available in current token."""
    try:
        svc = get_calendar_service()
        svc.calendarList().list(maxResults=1).execute()
        return True
    except Exception:
        return False


# ── Event Detection ────────────────────────────────────────────────────────────

MEETING_KEYWORDS = [
    r'\bmeeting\b', r'\bappointment\b', r'\bcall\b', r'\binterview\b',
    r'\bwebinar\b', r'\bconference\b', r'\blunch\b', r'\bbreakfast\b',
    r'\bdinne[r]?\b', r'\bschedule[d]?\b', r'\bjoin us\b', r'\binvit[e|ed]\b',
    r'\bzoom\b', r'\bgoogle meet\b', r'\bteams\b', r'\bms teams\b',
    r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b',
    r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
    r'\btomorrow\b', r'\bnext week\b',
    r'\b\d{1,2}:\d{2}\s*(am|pm)\b',
    r'\b\d{1,2}\s*(am|pm)\b',
]

def has_meeting_language(text: str) -> bool:
    """Return True if email body looks like it contains a meeting/appointment."""
    text_lower = text.lower()
    matches = sum(1 for p in MEETING_KEYWORDS if re.search(p, text_lower))
    return matches >= 2  # Require at least 2 signals


# ── LLM Event Extraction ───────────────────────────────────────────────────────

def extract_event_with_llm(email: dict) -> Optional[dict]:
    """
    Use local Ollama LLM to extract event details from email.
    Returns dict with: title, date, time, duration_hours, location, description
    """
    from llm_engine import call_ollama

    subject = email.get("subject", "")
    body    = (email.get("body") or "")[:1500]
    sender  = email.get("sender", "")
    today   = datetime.now().strftime("%A, %B %d, %Y")

    prompt = f"""Today is {today}.

Extract the meeting/appointment details from this email. Return ONLY valid JSON, nothing else.

From: {sender}
Subject: {subject}
Body:
{body}

Return this exact JSON structure (fill in what you can infer, use null for unknown):
{{
  "title": "Meeting title (use subject if unclear)",
  "date": "YYYY-MM-DD or null",
  "time": "HH:MM (24h) or null",
  "duration_hours": 1,
  "location": "location or video link or null",
  "description": "brief 1-sentence description"
}}

Only return the JSON. No explanation."""

    try:
        raw = call_ollama(prompt)
        # Extract JSON from response
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return data
    except Exception as e:
        print(f"⚠️  Calendar LLM extract error: {e}")

    # Fallback: minimal event
    return {
        "title": email.get("subject", "Meeting"),
        "date": None,
        "time": None,
        "duration_hours": 1,
        "location": None,
        "description": f"From: {sender}"
    }


# ── Calendar Event Creation ────────────────────────────────────────────────────

def create_calendar_event(
    title: str,
    date: Optional[str] = None,     # YYYY-MM-DD
    time: Optional[str] = None,     # HH:MM 24h
    duration_hours: float = 1.0,
    location: Optional[str] = None,
    description: Optional[str] = None,
    calendar_id: str = "primary"
) -> dict:
    """
    Create a Google Calendar event.
    If date is None, schedules for tomorrow at 10:00 AM.
    """
    svc = get_calendar_service()

    # Resolve date
    if date:
        try:
            event_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            event_date = datetime.now() + timedelta(days=1)
    else:
        event_date = datetime.now() + timedelta(days=1)

    # Resolve time
    if time:
        try:
            h, m = map(int, time.split(":"))
            event_date = event_date.replace(hour=h, minute=m, second=0, microsecond=0)
        except ValueError:
            event_date = event_date.replace(hour=10, minute=0, second=0, microsecond=0)
    else:
        event_date = event_date.replace(hour=10, minute=0, second=0, microsecond=0)

    end_date = event_date + timedelta(hours=duration_hours)

    # Build event body
    tz = "America/New_York"  # Default — could be made configurable
    event_body = {
        "summary": title,
        "start": {"dateTime": event_date.isoformat(), "timeZone": tz},
        "end":   {"dateTime": end_date.isoformat(),   "timeZone": tz},
    }
    if location:
        event_body["location"] = location
    if description:
        event_body["description"] = description

    result = svc.events().insert(calendarId=calendar_id, body=event_body).execute()
    return {
        "success": True,
        "event_id": result.get("id"),
        "event_link": result.get("htmlLink"),
        "title": title,
        "start": event_date.strftime("%B %d, %Y at %I:%M %p"),
    }


def create_event_from_email(email: dict) -> dict:
    """
    Full pipeline: extract details from email with LLM → create calendar event.
    """
    extracted = extract_event_with_llm(email)
    if not extracted:
        return {"success": False, "error": "Could not extract event details"}

    return create_calendar_event(
        title=extracted.get("title") or email.get("subject", "Meeting"),
        date=extracted.get("date"),
        time=extracted.get("time"),
        duration_hours=float(extracted.get("duration_hours") or 1),
        location=extracted.get("location"),
        description=extracted.get("description"),
    )


def get_upcoming_events(days: int = 7, calendar_id: str = "primary") -> list:
    """Get upcoming calendar events."""
    svc = get_calendar_service()
    now = datetime.now(timezone.utc).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    result = svc.events().list(
        calendarId=calendar_id,
        timeMin=now,
        timeMax=end,
        maxResults=20,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = []
    for e in result.get("items", []):
        start = e.get("start", {})
        events.append({
            "id":       e.get("id"),
            "title":    e.get("summary", "(no title)"),
            "start":    start.get("dateTime") or start.get("date"),
            "location": e.get("location"),
            "link":     e.get("htmlLink"),
        })
    return events
