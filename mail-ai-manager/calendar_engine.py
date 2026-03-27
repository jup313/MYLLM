"""
calendar_engine.py — Google Calendar integration via CalDAV
Uses the same IMAP credentials (email + App Password) already configured.
No OAuth needed — just CalDAV with App Password authentication.
"""

import re
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import caldav

BASE_DIR = Path(__file__).parent

CALDAV_URL = "https://www.google.com/calendar/dav/{username}/events/"

# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_credentials() -> tuple:
    """Get email + password from the database (same as IMAP)."""
    try:
        from database import get_config
        username = get_config("mail_imap_username")
        password = get_config("mail_imap_password")
        if username and password:
            return username, password
    except Exception:
        pass
    raise RuntimeError("No IMAP credentials configured. Set up email first.")


def _get_client() -> caldav.DAVClient:
    """Build CalDAV client using stored IMAP credentials."""
    username, password = _get_credentials()
    url = CALDAV_URL.format(username=username)
    return caldav.DAVClient(
        url=url,
        username=username,
        password=password,
    )


def _get_primary_calendar():
    """Get the primary (first) calendar."""
    client = _get_client()
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        raise RuntimeError("No calendars found for this account.")
    return calendars[0]


# ── Auth ───────────────────────────────────────────────────────────────────────

def is_calendar_authorized() -> bool:
    """Check if CalDAV connection works with stored credentials."""
    try:
        client = _get_client()
        principal = client.principal()
        cals = principal.calendars()
        return len(cals) > 0
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
    return matches >= 2


# ── LLM Event Extraction ───────────────────────────────────────────────────────

def extract_event_with_llm(email: dict) -> Optional[dict]:
    """Use local Ollama LLM to extract event details from email."""
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
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"⚠️  Calendar LLM extract error: {e}")

    return {
        "title": email.get("subject", "Meeting"),
        "date": None, "time": None, "duration_hours": 1,
        "location": None, "description": f"From: {sender}"
    }


# ── Calendar Event Creation ────────────────────────────────────────────────────

def create_calendar_event(
    title: str,
    date: Optional[str] = None,
    time: Optional[str] = None,
    duration_hours: float = 1.0,
    location: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Create a Google Calendar event via CalDAV."""
    cal = _get_primary_calendar()

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

    # Build iCalendar data
    import uuid
    uid = str(uuid.uuid4())
    loc_line = f"LOCATION:{location}\n" if location else ""
    desc_line = f"DESCRIPTION:{description}\n" if description else ""

    dtstart = event_date.strftime("%Y%m%dT%H%M%S")
    dtend   = end_date.strftime("%Y%m%dT%H%M%S")

    vcal = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//MailAI//CalDAV//EN
BEGIN:VEVENT
UID:{uid}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{title}
{loc_line}{desc_line}END:VEVENT
END:VCALENDAR"""

    event = cal.save_event(vcal)

    return {
        "success": True,
        "event_id": uid,
        "event_link": None,
        "title": title,
        "start": event_date.strftime("%B %d, %Y at %I:%M %p"),
    }


def create_event_from_email(email: dict) -> dict:
    """Full pipeline: extract details from email with LLM → create calendar event."""
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


def get_upcoming_events(days: int = 7) -> list:
    """Get upcoming calendar events via CalDAV."""
    cal = _get_primary_calendar()
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)

    results = cal.search(
        start=now,
        end=end,
        event=True,
        expand=True,
    )

    events = []
    for event in results:
        try:
            vevent = event.vobject_instance.vevent
            title = str(vevent.summary.value) if hasattr(vevent, 'summary') else "(no title)"
            start = vevent.dtstart.value
            if hasattr(start, 'isoformat'):
                start_str = start.isoformat()
            else:
                start_str = str(start)
            loc = str(vevent.location.value) if hasattr(vevent, 'location') else None
            uid = str(vevent.uid.value) if hasattr(vevent, 'uid') else None
            events.append({
                "id": uid,
                "title": title,
                "start": start_str,
                "location": loc,
                "link": None,
            })
        except Exception as e:
            print(f"⚠️  Error parsing event: {e}")
            continue

    # Sort by start time
    events.sort(key=lambda e: e.get("start", ""))
    return events
