#!/usr/bin/env python3
"""
mail_client.py — Hybrid IMAP + AppleScript mail client for macOS Mail
Provides unified interface for fetching, managing, and categorizing emails from multiple accounts
"""

import imaplib
import email
from email.message import Message as EmailMessage
import json
import subprocess
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MailMessage:
    """Unified mail message representation"""
    id: str
    sender: str
    subject: str
    body: str
    date: datetime
    is_read: bool
    is_flagged: bool
    mailbox: str
    message_id: str
    account: str
    raw_message: Optional[bytes] = None


class IMAPMailClient:
    """IMAP-based mail client (primary method)"""
    
    def __init__(self, imap_host: str, imap_port: int, username: str, password: str, account_name: str = "default"):
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.username = username
        self.password = password
        self.account_name = account_name
        self.imap = None
        self.is_connected = False
        
    def connect(self) -> bool:
        """Establish IMAP connection"""
        try:
            self.imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            self.imap.login(self.username, self.password)
            self.is_connected = True
            logger.info(f"✅ Connected to {self.account_name} via IMAP ({self.imap_host})")
            return True
        except Exception as e:
            logger.error(f"❌ IMAP connection failed for {self.account_name}: {str(e)}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Close IMAP connection"""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
                self.is_connected = False
            except:
                pass
    
    def list_mailboxes(self) -> List[str]:
        """List all available mailboxes"""
        if not self.is_connected:
            return []
        try:
            _, mailboxes = self.imap.list()
            return [mb.decode().split('"')[-2] for mb in mailboxes]
        except Exception as e:
            logger.error(f"Failed to list mailboxes: {e}")
            return []
    
    def fetch_emails(self, mailbox: str = "INBOX", limit: int = 50, unread_only: bool = False) -> List[MailMessage]:
        """Fetch emails from specified mailbox"""
        if not self.is_connected:
            return []
        
        messages = []
        try:
            self.imap.select(mailbox)
            
            # Search for emails
            if unread_only:
                _, email_ids = self.imap.search(None, "UNSEEN")
            else:
                _, email_ids = self.imap.search(None, "ALL")
            
            email_list = email_ids[0].split()[-limit:] if email_ids[0] else []
            
            for email_id in email_list:
                try:
                    _, raw_message = self.imap.fetch(email_id, "(RFC822)")
                    msg = email.message_from_bytes(raw_message[0][1])
                    
                    # Parse message details
                    sender = msg.get("From", "Unknown")
                    subject = msg.get("Subject", "(No Subject)")
                    date_str = msg.get("Date", "")
                    message_id = msg.get("Message-ID", str(email_id))
                    
                    # Decode subject if needed
                    if isinstance(subject, email.header.Header):
                        subject = str(subject)
                    
                    # Extract body
                    body = self._extract_body(msg)
                    
                    # Parse date
                    try:
                        from email.utils import parsedate_to_datetime
                        msg_date = parsedate_to_datetime(date_str)
                    except:
                        msg_date = datetime.now()
                    
                    # Check flags
                    _, flags = self.imap.fetch(email_id, "(FLAGS)")
                    flag_str = flags[0].decode()
                    is_read = "\\Seen" in flag_str
                    is_flagged = "\\Flagged" in flag_str
                    
                    mail_msg = MailMessage(
                        id=email_id.decode(),
                        sender=sender,
                        subject=subject,
                        body=body[:2000],  # Limit body length
                        date=msg_date,
                        is_read=is_read,
                        is_flagged=is_flagged,
                        mailbox=mailbox,
                        message_id=message_id,
                        account=self.account_name,
                        raw_message=raw_message[0][1]
                    )
                    messages.append(mail_msg)
                except Exception as e:
                    logger.warning(f"Failed to parse email {email_id}: {e}")
                    continue
            
            return messages
        except Exception as e:
            logger.error(f"Failed to fetch emails from {mailbox}: {e}")
            return []
    
    def mark_read(self, email_id: str) -> bool:
        """Mark email as read"""
        if not self.is_connected:
            return False
        try:
            self.imap.store(email_id, "+FLAGS", "\\Seen")
            return True
        except Exception as e:
            logger.error(f"Failed to mark email as read: {e}")
            return False
    
    def move_to_folder(self, email_id: str, folder: str) -> bool:
        """Move email to another folder"""
        if not self.is_connected:
            return False
        try:
            self.imap.copy(email_id, folder)
            self.imap.store(email_id, "+FLAGS", "\\Deleted")
            self.imap.expunge()
            return True
        except Exception as e:
            logger.error(f"Failed to move email: {e}")
            return False
    
    def flag_email(self, email_id: str, flagged: bool = True) -> bool:
        """Flag or unflag an email"""
        if not self.is_connected:
            return False
        try:
            if flagged:
                self.imap.store(email_id, "+FLAGS", "\\Flagged")
            else:
                self.imap.store(email_id, "-FLAGS", "\\Flagged")
            return True
        except Exception as e:
            logger.error(f"Failed to flag email: {e}")
            return False
    
    @staticmethod
    def _extract_body(msg: email.message.Message) -> str:
        """Extract plain text body from email"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")
        return body.strip()


class AppleScriptMailClient:
    """AppleScript-based fallback for macOS Mail.app"""
    
    def __init__(self, account_name: str = "default"):
        self.account_name = account_name
        self.is_available = self._check_availability()
    
    @staticmethod
    def _check_availability() -> bool:
        """Check if AppleScript/osascript is available"""
        try:
            result = subprocess.run(["which", "osascript"], capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    def run_script(self, script: str) -> Tuple[bool, str]:
        """Execute AppleScript and return result"""
        if not self.is_available:
            return False, "AppleScript not available"
        
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except Exception as e:
            return False, str(e)
    
    def get_accounts(self) -> List[str]:
        """Get list of Mail.app accounts via AppleScript"""
        script = """
        tell application "Mail"
            set accountList to {}
            repeat with acc in accounts
                set end of accountList to name of acc
            end repeat
            return accountList as string
        end tell
        """
        success, result = self.run_script(script)
        if success:
            return [acc.strip() for acc in result.split(",") if acc.strip()]
        return []
    
    def get_unread_count(self, account: str = None) -> int:
        """Get unread email count"""
        if account:
            script = f'tell application "Mail" to get unread count of account "{account}"'
        else:
            script = 'tell application "Mail" to get unread count'
        
        success, result = self.run_script(script)
        if success:
            try:
                return int(result)
            except:
                return 0
        return 0
    
    def mark_read_applescript(self, message_id: str, account: str) -> bool:
        """Mark email as read using AppleScript"""
        script = f"""
        tell application "Mail"
            set theMessage to message id "{message_id}" of account "{account}"
            set read status of theMessage to true
        end tell
        """
        success, _ = self.run_script(script)
        return success
    
    def move_to_trash_applescript(self, message_id: str, account: str) -> bool:
        """Move email to trash using AppleScript"""
        script = f"""
        tell application "Mail"
            set theMessage to message id "{message_id}" of account "{account}"
            delete theMessage
        end tell
        """
        success, _ = self.run_script(script)
        return success


class HybridMailClient:
    """Hybrid IMAP + AppleScript mail client with failover"""
    
    def __init__(self, imap_config: Dict):
        """
        Initialize hybrid client
        imap_config: {
            'imap_host': 'imap.gmail.com',
            'imap_port': 993,
            'username': 'user@gmail.com',
            'password': 'app-password',
            'account_name': 'Gmail'
        }
        """
        self.imap_client = IMAPMailClient(**imap_config)
        self.applescript_client = AppleScriptMailClient(imap_config.get('account_name', 'default'))
        self.config = imap_config
        
    def connect(self) -> bool:
        """Connect with IMAP primary, AppleScript fallback"""
        if self.imap_client.connect():
            logger.info(f"✅ Using IMAP for {self.config.get('account_name')}")
            return True
        elif self.applescript_client.is_available:
            logger.warning(f"⚠️  IMAP failed, falling back to AppleScript for {self.config.get('account_name')}")
            return True
        else:
            logger.error(f"❌ No connection method available for {self.config.get('account_name')}")
            return False
    
    def disconnect(self):
        """Disconnect IMAP client"""
        self.imap_client.disconnect()
    
    def fetch_emails(self, mailbox: str = "INBOX", limit: int = 50) -> List[MailMessage]:
        """Fetch emails using IMAP (with AppleScript fallback if needed)"""
        if self.imap_client.is_connected:
            return self.imap_client.fetch_emails(mailbox, limit)
        else:
            logger.warning("IMAP not connected, cannot fetch emails via AppleScript yet")
            return []
    
    def mark_read(self, email: MailMessage) -> bool:
        """Mark email as read"""
        if self.imap_client.is_connected:
            return self.imap_client.mark_read(email.id)
        elif self.applescript_client.is_available:
            return self.applescript_client.mark_read_applescript(email.message_id, email.account)
        return False
    
    def move_to_spam(self, email: MailMessage) -> bool:
        """Move email to spam/junk folder"""
        spam_folders = ["[Gmail]/Spam", "Junk", "Spam", "Junk Mail"]
        
        if self.imap_client.is_connected:
            for folder in spam_folders:
                if self.imap_client.move_to_folder(email.id, folder):
                    return True
        
        if self.applescript_client.is_available:
            return self.applescript_client.move_to_trash_applescript(email.message_id, email.account)
        
        return False
    
    def archive_email(self, email: MailMessage) -> bool:
        """Archive email (move to appropriate folder)"""
        if self.imap_client.is_connected:
            # Try common archive folder names
            archive_folders = ["[Gmail]/All Mail", "Archive", "All Mail"]
            for folder in archive_folders:
                if self.imap_client.move_to_folder(email.id, folder):
                    return True
        return False
    
    def flag_email(self, email: MailMessage, flagged: bool = True) -> bool:
        """Flag or unflag an email"""
        if self.imap_client.is_connected:
            return self.imap_client.flag_email(email.id, flagged)
        return False


def create_mail_client(config: Dict) -> HybridMailClient:
    """Factory function to create a configured mail client"""
    return HybridMailClient(config)
