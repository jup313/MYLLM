#!/usr/bin/env python3
"""
summarizer.py — Daily/weekly email summary generator
Produces HTML and text summaries from classified emails.
"""

from datetime import datetime, timedelta
from database import get_emails, save_summary, get_config
from llm_engine import generate_summary_text

CATEGORY_ICONS = {
    "urgent":       "🚨",
    "work":         "💼",
    "personal":     "👤",
    "marketing":    "📣",
    "spam":         "🗑️",
    "notification": "🔔",
}

CATEGORY_COLORS = {
    "urgent":       "#ef4444",
    "work":         "#3b82f6",
    "personal":     "#8b5cf6",
    "marketing":    "#f59e0b",
    "spam":         "#6b7280",
    "notification": "#10b981",
}


def generate_daily_summary() -> dict:
    """Generate today's email summary."""
    today = datetime.now().strftime("%Y-%m-%d")
    emails = get_emails(limit=200, processed=None)

    # Filter to today's emails (approximate via fetched_at)
    today_emails = [e for e in emails if e.get("fetched_at", "")[:10] == today]
    if not today_emails:
        today_emails = emails[:50]  # Fallback to latest 50

    return _build_summary(today_emails, "daily", f"📬 Daily Summary — {today}")


def generate_weekly_summary() -> dict:
    """Generate this week's email summary."""
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    emails = get_emails(limit=500)
    week_emails = [e for e in emails if e.get("fetched_at", "")[:10] >= week_ago]
    return _build_summary(week_emails, "weekly", f"📊 Weekly Summary — Week of {today}")


def _build_summary(emails: list, period: str, title: str) -> dict:
    """Build HTML + text summary from a list of emails."""
    if not emails:
        return {
            "html": f"<h2>{title}</h2><p>No emails to summarize.</p>",
            "text": f"{title}\n\nNo emails to summarize.",
            "period": period,
            "count": 0
        }

    # Count by category
    by_category = {}
    urgent_emails = []
    work_emails   = []

    for e in emails:
        cat = e.get("category") or "notification"
        by_category[cat] = by_category.get(cat, 0) + 1
        if cat == "urgent":
            urgent_emails.append(e)
        elif cat == "work":
            work_emails.append(e)

    total = len(emails)

    # Generate LLM narrative
    narrative = generate_summary_text(emails, period)

    # Build HTML
    html = _build_html(title, total, by_category, urgent_emails, work_emails, narrative, period)

    # Build plain text
    text = _build_text(title, total, by_category, urgent_emails, work_emails, narrative)

    # Save to DB
    save_summary(period, html, text)

    return {"html": html, "text": text, "period": period, "count": total}


def _build_html(title, total, by_category, urgent_emails, work_emails, narrative, period) -> str:
    date_str = datetime.now().strftime("%B %d, %Y %I:%M %p")

    # Category bars
    cat_rows = ""
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        icon  = CATEGORY_ICONS.get(cat, "📧")
        color = CATEGORY_COLORS.get(cat, "#6b7280")
        pct   = int((count / total) * 100) if total else 0
        cat_rows += f"""
        <tr>
          <td style="padding:6px 12px;color:#e2e8f0;">{icon} {cat.title()}</td>
          <td style="padding:6px 12px;">
            <div style="background:#1e293b;border-radius:4px;overflow:hidden;width:200px;">
              <div style="background:{color};width:{pct}%;height:12px;border-radius:4px;"></div>
            </div>
          </td>
          <td style="padding:6px 12px;color:#94a3b8;font-weight:bold;">{count}</td>
        </tr>"""

    # Priority items
    priority_rows = ""
    priority_items = urgent_emails[:5] + work_emails[:5]
    for i, e in enumerate(priority_items[:8], 1):
        cat   = e.get("category", "?")
        icon  = CATEGORY_ICONS.get(cat, "📧")
        color = CATEGORY_COLORS.get(cat, "#6b7280")
        priority_rows += f"""
        <tr style="border-bottom:1px solid #1e293b;">
          <td style="padding:8px 12px;color:#94a3b8;">{i}.</td>
          <td style="padding:8px 12px;">
            <span style="background:{color}22;color:{color};padding:2px 8px;border-radius:12px;font-size:11px;">{icon} {cat}</span>
          </td>
          <td style="padding:8px 12px;color:#e2e8f0;">{e.get('subject','?')[:60]}</td>
          <td style="padding:8px 12px;color:#94a3b8;font-size:12px;">{e.get('sender','?')[:30]}</td>
        </tr>"""

    if not priority_rows:
        priority_rows = '<tr><td colspan="4" style="padding:16px;color:#64748b;text-align:center;">No priority items</td></tr>'

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><style>
  body {{background:#0f172a;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;padding:20px;}}
  h1{{color:#4ade80;margin:0 0 4px;}} h2{{color:#93c5fd;}} table{{border-collapse:collapse;width:100%;}}
  .card{{background:#1e293b;border-radius:12px;padding:20px;margin:16px 0;}}
</style></head>
<body>
<h1>{title}</h1>
<p style="color:#64748b;margin:0 0 20px;">{date_str}</p>

<div class="card">
  <h2>📊 Overview</h2>
  <p style="font-size:24px;font-weight:bold;color:#4ade80;margin:0;">{total} emails processed</p>
  <table style="margin-top:12px;">{cat_rows}</table>
</div>

<div class="card">
  <h2>🤖 AI Summary</h2>
  <p style="color:#cbd5e1;line-height:1.7;">{narrative}</p>
</div>

<div class="card">
  <h2>⚡ Priority Items</h2>
  <table><thead><tr style="color:#64748b;font-size:12px;text-transform:uppercase;">
    <th style="padding:8px 12px;text-align:left;">#</th>
    <th style="padding:8px 12px;text-align:left;">Type</th>
    <th style="padding:8px 12px;text-align:left;">Subject</th>
    <th style="padding:8px 12px;text-align:left;">From</th>
  </tr></thead><tbody>{priority_rows}</tbody></table>
</div>

<p style="color:#334155;font-size:12px;text-align:center;margin-top:24px;">
  Generated by Gmail AI Manager · {date_str}
</p>
</body></html>"""


def _build_text(title, total, by_category, urgent_emails, work_emails, narrative) -> str:
    lines = [
        title,
        "=" * len(title),
        f"Generated: {datetime.now().strftime('%B %d, %Y %I:%M %p')}",
        "",
        f"TOTAL: {total} emails",
        "",
        "BY CATEGORY:",
    ]
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        icon = CATEGORY_ICONS.get(cat, "📧")
        lines.append(f"  {icon} {cat.title()}: {count}")

    lines += ["", "AI SUMMARY:", narrative, ""]

    priority_items = urgent_emails[:5] + work_emails[:5]
    if priority_items:
        lines.append("PRIORITY ITEMS:")
        for i, e in enumerate(priority_items[:8], 1):
            lines.append(f"  {i}. [{e.get('category','?').upper()}] {e.get('subject','?')[:60]}")
            lines.append(f"     From: {e.get('sender','?')}")

    return "\n".join(lines)
