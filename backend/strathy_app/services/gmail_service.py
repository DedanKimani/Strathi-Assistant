# backend/strathy_app/services/gmail_service.py
import base64
import logging
import re
from typing import List, Dict, Optional
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE
from .ai_reply_service import generate_ai_reply
from ..utils.email_parser import parse_message
from ..utils.mime_helpers import build_reply_mime

logger = logging.getLogger(__name__)


def build_gmail_service(creds: Credentials):
    """Load/refresh creds and return a Gmail service client."""
    if not creds:
        return None
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    try:
        return build("gmail", "v1", credentials=creds)
    except HttpError as e:
        logger.error("Failed to build Gmail service: %s", e)
        return None


def list_unread_messages(service, q: str = "is:unread", max_results: int = 5) -> List[Dict]:
    """List unread messages (returns list of message metadata dicts)."""
    try:
        resp = service.users().messages().list(
            userId="me", q=q, labelIds=["INBOX"], maxResults=max_results
        ).execute()
        return resp.get("messages", []) or []
    except HttpError as e:
        logger.error("Error listing messages: %s", e)
        return []


def get_message(service, message_id: str, fmt: str = "full") -> Optional[Dict]:
    """Get a full message by ID from Gmail."""
    try:
        return service.users().messages().get(userId="me", id=message_id, format=fmt).execute()
    except HttpError as e:
        logger.error("Error getting message %s: %s", message_id, e)
        return None


def send_mime(service, raw_mime, thread_id: Optional[str] = None) -> Optional[Dict]:
    """Send a MIME message via Gmail API."""
    try:
        if isinstance(raw_mime, str):
            raw_bytes = raw_mime.encode("utf-8")
        else:
            raw_bytes = raw_mime.as_bytes()

        raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode()
        body = {"raw": raw_b64}
        if thread_id:
            body["threadId"] = thread_id

        sent = service.users().messages().send(userId="me", body=body).execute()
        logger.info("Sent message id=%s threadId=%s", sent.get("id"), sent.get("threadId"))
        return sent
    except HttpError as e:
        logger.error("Gmail send failed: %s", e)
        return None


# ---- Helper to extract email address from "From" header ----
def _extract_email(from_header: Optional[str]) -> Optional[str]:
    if not from_header:
        return None
    m = re.search(r"<([^>]+)>", from_header)
    if m:
        return m.group(1).strip()
    tokens = re.split(r"[,\s]+", from_header)
    for t in tokens[::-1]:
        if "@" in t:
            return t.strip("<>").strip()
    return None


# ---------------------------
# MAIN FLOWS
# ---------------------------

def process_incoming_email(service, message: Dict) -> Optional[Dict]:
    """
    Process a single incoming student query and immediately generate an AI reply.
    Returns both student query and AI reply for display.
    """
    try:
        msg_id = message.get("id")
        if not msg_id:
            return None

        full = get_message(service, msg_id)
        if not full:
            return None

        parsed = parse_message(full)
        sender_header = parsed.get("sender", "")
        sender_email = _extract_email(sender_header)
        if not sender_email:
            return None

        subject = parsed.get("subject") or "(no subject)"
        body = parsed.get("body") or ""
        thread_id = parsed.get("thread_id")

        # Mark as read
        try:
            service.users().messages().modify(
                userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
        except HttpError as e:
            logger.warning("Failed to clear UNREAD for %s: %s", msg_id, e)

        # === NEW: generate AI reply here ===
        ai_reply_result = generate_and_send_ai_reply(service, {
            "from": sender_header,
            "subject": subject,
            "body": body,
            "threadId": thread_id
        })

        return {
            "id": msg_id,
            "threadId": thread_id,
            "from": sender_header,
            "subject": subject,
            "body": body,
            "role": "student",
            "status": "processed",
            "ai_reply": ai_reply_result.get("ai_reply") if ai_reply_result else None,
            "ai_role": "strathy" if ai_reply_result else None,
        }

    except Exception as exc:
        logger.exception("process_incoming_email failed: %s", exc)
        return None


def generate_and_send_ai_reply(service, student_msg: Dict) -> Optional[Dict]:
    """
    Generate an AI reply for a student message and send it.
    """
    try:
        sender_header = student_msg.get("from", "")
        sender_email = _extract_email(sender_header)
        if not sender_email:
            return None

        subject = student_msg.get("subject", "(no subject)")
        reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        body = student_msg.get("body", "")
        thread_id = student_msg.get("threadId")

        sender_name = (
            sender_header.split("<")[0].strip().replace('"', "")
            if "<" in sender_header
            else sender_email.split("@")[0]
        )

        # Generate AI text
        ai_reply_text = generate_ai_reply(
            sender_name=sender_name,
            sender_email=sender_email,
            subject=subject,
            body=body
        )
        if not ai_reply_text:
            return None

        # Build MIME + send
        raw_mime = build_reply_mime(
            to_email=sender_email,
            subject=reply_subject,
            body_text=ai_reply_text,
            in_reply_to=[],  # safe fallback
            original_headers=[],
        )
        sent = send_mime(service, raw_mime, thread_id=thread_id)

        return {
            "threadId": thread_id,
            "to": sender_email,
            "from": "strathy@strathmore.edu",   # Strathy’s identity
            "subject": reply_subject,
            "ai_reply": ai_reply_text,
            "sent_id": sent.get("id") if sent else None,
            "role": "strathy"
        }

    except Exception as exc:
        logger.exception("generate_and_send_ai_reply failed: %s", exc)
        return None


def get_ai_reply_for_thread(service, thread_id: str) -> Optional[str]:
    """
    Fetch the latest AI reply for a given thread (if Strathy already responded).
    """
    try:
        thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()
        messages = thread.get("messages", [])
        for msg in reversed(messages):  # newest first
            parsed = parse_message(msg)
            sender_header = parsed.get("sender", "")
            if sender_header and "strathy@strathmore.edu" in sender_header.lower():
                return parsed.get("body")
        return None
    except HttpError as e:
        logger.error("Failed to fetch AI reply for thread %s: %s", thread_id, e)
        return None
