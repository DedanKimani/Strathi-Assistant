# backend/strathy_app/services/gmail_service.py
import base64
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime, timezone

from backend.strathy_app.services.conversation_service import save_conversation_and_messages
from backend.strathy_app.models.models import SessionLocal, Message, Student, Conversation

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE
from .ai_reply_service import generate_ai_reply
from ..utils.email_parser import parse_message
from ..utils.mime_helpers import build_reply_mime

logger = logging.getLogger(__name__)


# ========================
# Gmail Connection Helpers
# ========================
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
        logger.info("✅ Sent message id=%s threadId=%s", sent.get("id"), sent.get("threadId"))
        return sent
    except HttpError as e:
        logger.error("Gmail send failed: %s", e)
        return None


# -------------------------
# Utility: Extract email
# -------------------------
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


# ===========================
# Email Processing / AI Reply
# ===========================

# 🚫 Blocklist (do not reply)
BLOCKED_EMAILS = {
    "strathmorecommunication@gmail.com",
    "allstudents@strathmore.edu",
    "allstaff@strathmore.edu",
    "ictservices@strathmore.edu",
    "tndumah@strathmore.edu",
    "gnyaloti@strathmore.edu",
    "bmonda@strathmore.edu",
    "danson.mulinge@strathmore.edu",
    "dmulinge@strathmore.edu",
    "rkidewa@strathmore.edu",
    "rkithuka@strathmore.edu",
    "hmuchiri@strathmore.edu",
}

# ✅ Whitelist (trusted external senders)
ALLOWED_EXTERNAL_SENDERS = {
    "dedankimani007@gmail.com",
}


def is_sender_allowed(email: str) -> bool:
    """Check if a sender is allowed to receive an AI reply."""
    email = (email or "").lower().strip()
    if email in BLOCKED_EMAILS:
        return False
    if email.endswith("@strathmore.edu"):
        return True
    if email in ALLOWED_EXTERNAL_SENDERS:
        return True
    return False


# ===========================
# Core Processing
# ===========================
def process_incoming_email(service, message: Dict) -> Optional[Dict]:
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
        thread_id = parsed.get("thread_id")
        thread_messages = extract_thread_messages(service, thread_id) if thread_id else []

        if not sender_email:
            return None

        subject = parsed.get("subject") or "(no subject)"
        body = parsed.get("body") or ""

        internal_date = full.get("internalDate")
        received_at = (
            datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc).isoformat()
            if internal_date else None
        )

        # Mark message as read
        try:
            service.users().messages().modify(
                userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
        except HttpError as e:
            logger.warning("Failed to clear UNREAD for %s: %s", msg_id, e)

        # 🚫 Skip disallowed senders
        if not is_sender_allowed(sender_email):
            reason = "Blocked sender" if sender_email in BLOCKED_EMAILS else "External domain not allowed"
            logger.info(f"⛔ Skipping AI reply to {sender_email} ({reason})")
            return {
                "id": msg_id,
                "threadId": thread_id,
                "from": sender_header,
                "subject": subject,
                "body": body,
                "role": "student",
                "status": "blocked",
                "reason": reason,
                "received_at": received_at,
                "ai_reply": None,
                "ai_replied_at": None,
                "ai_role": None,
                "thread_messages": thread_messages,
            }

        # ✅ Save student & conversation in DB
        db = SessionLocal()
        try:
            save_result = save_conversation_and_messages(
                db=db,
                email_text=body,
                subject=subject,
                sender_email=sender_email,
                thread_id=thread_id or msg_id,
            )
        finally:
            db.close()

        # ✅ Generate AI reply (only if allowed)
        ai_reply_result = generate_and_send_ai_reply(service, {
            "from": sender_header,
            "subject": subject,
            "body": body,
            "threadId": thread_id
        })

        status = ai_reply_result.get("status", "pending") if ai_reply_result else "pending"

        return {
            "id": msg_id,
            "threadId": thread_id,
            "from": sender_header,
            "subject": subject,
            "body": body,
            "role": "student",
            "status": status,
            "received_at": received_at,
            "ai_reply": ai_reply_result.get("ai_reply") if ai_reply_result else None,
            "ai_replied_at": ai_reply_result.get("sent_at") if ai_reply_result else None,
            "ai_role": "strathy" if ai_reply_result else None,
            "thread_messages": thread_messages,
            "student_info": save_result.get("extracted") if save_result else {},
        }

    except Exception as exc:
        logger.exception("process_incoming_email failed: %s", exc)
        return None



def generate_and_send_ai_reply(service, student_msg: Dict) -> Optional[Dict]:
    try:
        sender_header = student_msg.get("from", "")
        sender_email = _extract_email(sender_header)
        if not sender_email or not is_sender_allowed(sender_email):
            logger.info(f"⛔ Not sending AI reply to disallowed sender: {sender_email}")
            return {"status": "blocked", "ai_reply": None, "sent_at": None}

        subject = student_msg.get("subject", "(no subject)")
        reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        body = student_msg.get("body", "")
        thread_id = student_msg.get("threadId")

        sender_name = (
            sender_header.split("<")[0].strip().replace('"', "")
            if "<" in sender_header
            else sender_email.split("@")[0]
        )

        ai_reply_text = generate_ai_reply(
            sender_name=sender_name,
            sender_email=sender_email,
            subject=subject,
            body=body
        )

        if not ai_reply_text:
            logger.warning("⚠️ AI did not generate a reply for %s", sender_email)
            return {"status": "pending", "ai_reply": None, "sent_at": None}

        # 📨 Actually send the reply email
        sent = send_mime(service, build_reply_mime(
            to_email=sender_email,
            subject=reply_subject,
            body_text=ai_reply_text,
            in_reply_to=[],
            original_headers=[],
        ), thread_id=thread_id)

        sent_at = datetime.now(timezone.utc).isoformat()
        return {
            "status": "replied" if sent else "pending",
            "threadId": thread_id,
            "to": sender_email,
            "from": "strathy@strathmore.edu",
            "subject": reply_subject,
            "ai_reply": ai_reply_text,
            "sent_id": sent.get("id") if sent else None,
            "sent_at": sent_at if sent else None,
            "role": "strathy"
        }

    except Exception as exc:
        logger.exception("generate_and_send_ai_reply failed: %s", exc)
        return {"status": "pending", "ai_reply": None, "sent_at": None}


def get_ai_reply_for_thread(service, thread_id: str) -> Optional[str]:
    """Fetch the latest AI reply in a Gmail thread."""
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

def extract_thread_messages(service, thread_id: str) -> List[Dict]:
    """Return all messages in a Gmail thread, parsed into a structured list."""
    try:
        thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()
        messages = thread.get("messages", [])
        extracted = []

        for msg in messages:
            parsed = parse_message(msg)
            sender_header = parsed.get("sender", "")
            sender_email = _extract_email(sender_header)
            role = "strathy" if sender_email and "strathy@strathmore.edu" in sender_email.lower() else "student"
            extracted.append({
                "id": msg.get("id"),
                "sender": sender_header,
                "sender_email": sender_email,
                "subject": parsed.get("subject"),
                "body": parsed.get("body"),
                "role": role,
                "date": datetime.fromtimestamp(
                    int(msg.get("internalDate", 0)) / 1000, tz=timezone.utc
                ).isoformat() if msg.get("internalDate") else None,
            })
        return extracted

    except HttpError as e:
        logger.error("❌ Failed to extract thread %s: %s", thread_id, e)
        return []
