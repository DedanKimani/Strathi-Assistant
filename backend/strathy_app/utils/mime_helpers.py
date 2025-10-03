# backend/strathy_app/utils/mime_helpers.py
import base64
import email.utils
from email.message import EmailMessage
from typing import List, Dict, Optional

def _get_header(headers: List[Dict], name: str) -> Optional[str]:
    for h in headers or []:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


def build_reply_mime(
    to_email: str,
    subject: str,
    body_text: str,
    in_reply_to: List[Dict],
    original_headers: List[Dict],
):
    """
    Build a reply MIME. We set:
      - To, From, Subject, Date, Message-ID
      - In-Reply-To (original Message-Id)
      - References (chain: previous References + original Message-Id)
    NOTE: Returns an EmailMessage object, not base64-encoded.
    """
    orig_msg_id = _get_header(original_headers, "Message-Id") or _get_header(original_headers, "Message-ID")
    prev_refs = _get_header(original_headers, "References")

    msg = EmailMessage()
    msg["To"] = to_email
    msg["From"] = "strathy@strathmore.edu"  # ✅ Explicit sender
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid()

    if orig_msg_id:
        msg["In-Reply-To"] = orig_msg_id
        msg["References"] = f"{prev_refs} {orig_msg_id}" if prev_refs else orig_msg_id

    msg.set_content(body_text or "")

    # ✅ Return EmailMessage object — let send_mime() handle encoding
    return msg
