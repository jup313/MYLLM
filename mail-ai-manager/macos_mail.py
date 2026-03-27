#!/usr/bin/env python3
"""
macos_mail.py — macOS Mail.app integration via AppleScript
Reads emails directly from Mail.app — no IMAP credentials needed.
Mail.app handles all authentication (Gmail, iCloud, Outlook, etc.)
"""

import subprocess
import json
import re
from datetime import datetime
from database import get_config, log_action


def _run_applescript(script: str, timeout: int = 120) -> str:
    """Execute AppleScript and return output."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            raise Exception(f"AppleScript error: {result.stderr.strip()}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise Exception("AppleScript timed out")


def is_authenticated() -> bool:
    """Check if Mail.app is running and has accounts configured."""
    try:
        script = '''
        tell application "System Events"
            set mailRunning to (name of processes) contains "Mail"
        end tell
        if mailRunning then
            tell application "Mail"
                set acctCount to count of accounts
                return acctCount as text
            end tell
        else
            return "0"
        end if
        '''
        result = _run_applescript(script)
        return int(result) > 0
    except Exception:
        return False


def test_mail_connection() -> dict:
    """Test connection to macOS Mail.app."""
    try:
        script = '''
        tell application "Mail"
            set acctList to {}
            repeat with acct in accounts
                set end of acctList to (name of acct) & " (" & (email addresses of acct as text) & ")"
            end repeat
            return acctList as text
        end tell
        '''
        result = _run_applescript(script)
        if result:
            accounts = [a.strip() for a in result.split(",") if a.strip()]
            return {
                "success": True,
                "message": f"Connected to Mail.app with {len(accounts)} account(s)",
                "accounts": accounts
            }
        else:
            return {"success": False, "error": "No accounts found in Mail.app"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_accounts() -> list:
    """Get list of email accounts from Mail.app."""
    try:
        script = '''
        tell application "Mail"
            set acctInfo to ""
            repeat with acct in accounts
                set acctName to name of acct
                set acctEmails to email addresses of acct as text
                set acctInfo to acctInfo & acctName & "|" & acctEmails & "\\n"
            end repeat
            return acctInfo
        end tell
        '''
        result = _run_applescript(script)
        accounts = []
        for line in result.strip().split("\n"):
            if "|" in line:
                parts = line.split("|")
                accounts.append({"name": parts[0].strip(), "email": parts[1].strip()})
        return accounts
    except Exception:
        return []


def fetch_unread(max_results: int = 50) -> list:
    """Fetch unread emails from Mail.app inbox using fast index-based access."""
    try:
        # Scan up to 200 recent messages by index to find unread ones
        scan_limit = max_results * 4
        if scan_limit < 200:
            scan_limit = 200
        script = f'''
        tell application "Mail"
            set emailList to ""
            set foundCount to 0
            set totalCount to count of messages of inbox
            if totalCount > {scan_limit} then set totalCount to {scan_limit}
            repeat with i from 1 to totalCount
                if foundCount ≥ {max_results} then exit repeat
                try
                    set msg to message i of inbox
                    if read status of msg is false then
                        set msgId to id of msg as text
                        set msgSubject to subject of msg
                        set msgSender to sender of msg
                        set msgDate to date received of msg as text
                        set msgSnippet to ""
                        try
                            set msgContent to content of msg
                            if length of msgContent > 200 then
                                set msgSnippet to text 1 thru 200 of msgContent
                            else
                                set msgSnippet to msgContent
                            end if
                        end try
                        set emailList to emailList & msgId & "||SEP||" & msgSubject & "||SEP||" & msgSender & "||SEP||" & msgDate & "||SEP||" & msgSnippet & "||REC||"
                        set foundCount to foundCount + 1
                    end if
                end try
            end repeat
            return emailList
        end tell
        '''
        result = _run_applescript(script)
        emails = []
        for record in result.split("||REC||"):
            record = record.strip()
            if not record:
                continue
            parts = record.split("||SEP||")
            if len(parts) >= 4:
                # Parse sender
                sender_raw = parts[2].strip() if len(parts) > 2 else ""
                match = re.search(r"<(.+?)>", sender_raw)
                sender_email = match.group(1) if match else sender_raw
                sender_name = re.sub(r"<.+?>", "", sender_raw).strip().strip('"')
                
                emails.append({
                    "id": parts[0].strip(),
                    "thread_id": "",
                    "subject": parts[1].strip() if len(parts) > 1 else "(no subject)",
                    "sender": sender_name or sender_email,
                    "sender_email": sender_email,
                    "snippet": parts[4].strip() if len(parts) > 4 else "",
                    "body": parts[4].strip() if len(parts) > 4 else "",
                    "date": parts[3].strip() if len(parts) > 3 else "",
                    "labels": "[]",
                    "unsubscribe_url": None,
                    "processed": 0,
                })
        return emails
    except Exception as e:
        print(f"  ⚠️  Error fetching unread: {e}")
        return []


def fetch_recent(max_results: int = 30) -> list:
    """Fetch recent emails from Mail.app inbox using fast index-based access."""
    try:
        script = f'''
        tell application "Mail"
            set emailList to ""
            set totalCount to count of messages of inbox
            if totalCount > {max_results} then set totalCount to {max_results}
            repeat with i from 1 to totalCount
                try
                    set msg to message i of inbox
                    set msgId to id of msg as text
                    set msgSubject to subject of msg
                    set msgSender to sender of msg
                    set msgDate to date received of msg as text
                    set msgSnippet to ""
                    try
                        set msgContent to content of msg
                        if length of msgContent > 200 then
                            set msgSnippet to text 1 thru 200 of msgContent
                        else
                            set msgSnippet to msgContent
                        end if
                    end try
                    set emailList to emailList & msgId & "||SEP||" & msgSubject & "||SEP||" & msgSender & "||SEP||" & msgDate & "||SEP||" & msgSnippet & "||REC||"
                end try
            end repeat
            return emailList
        end tell
        '''
        result = _run_applescript(script)
        emails = []
        for record in result.split("||REC||"):
            record = record.strip()
            if not record:
                continue
            parts = record.split("||SEP||")
            if len(parts) >= 4:
                sender_raw = parts[2].strip() if len(parts) > 2 else ""
                match = re.search(r"<(.+?)>", sender_raw)
                sender_email = match.group(1) if match else sender_raw
                sender_name = re.sub(r"<.+?>", "", sender_raw).strip().strip('"')
                
                emails.append({
                    "id": parts[0].strip(),
                    "thread_id": "",
                    "subject": parts[1].strip() if len(parts) > 1 else "(no subject)",
                    "sender": sender_name or sender_email,
                    "sender_email": sender_email,
                    "snippet": parts[4].strip() if len(parts) > 4 else "",
                    "body": parts[4].strip() if len(parts) > 4 else "",
                    "date": parts[3].strip() if len(parts) > 3 else "",
                    "labels": "[]",
                    "unsubscribe_url": None,
                    "processed": 0,
                })
        return emails
    except Exception as e:
        print(f"  ⚠️  Error fetching recent: {e}")
        return []


def get_email_body(email_id: str) -> str:
    """Get full body of a specific email."""
    try:
        script = f'''
        tell application "Mail"
            set msg to first message of inbox whose id is {email_id}
            return content of msg
        end tell
        '''
        return _run_applescript(script)
    except Exception:
        return ""


def mark_read(email_id: str) -> bool:
    """Mark email as read in Mail.app."""
    try:
        script = f'''
        tell application "Mail"
            set msg to first message of inbox whose id is {email_id}
            set read status of msg to true
        end tell
        '''
        _run_applescript(script)
        return True
    except Exception:
        return False


def trash_email(email_id: str) -> bool:
    """Move email to trash in Mail.app."""
    try:
        script = f'''
        tell application "Mail"
            set msg to first message of inbox whose id is {email_id}
            delete msg
        end tell
        '''
        _run_applescript(script)
        log_action(email_id, "trash", "success")
        return True
    except Exception as e:
        log_action(email_id, "trash", "error", str(e))
        return False


def archive_email(email_id: str) -> bool:
    """Archive email (move to Archive mailbox) in Mail.app."""
    try:
        script = f'''
        tell application "Mail"
            set msg to first message of inbox whose id is {email_id}
            set archiveBox to mailbox "Archive" of account of mailbox of msg
            move msg to archiveBox
        end tell
        '''
        _run_applescript(script)
        log_action(email_id, "archive", "success")
        return True
    except Exception as e:
        log_action(email_id, "archive", "error", str(e))
        return False
