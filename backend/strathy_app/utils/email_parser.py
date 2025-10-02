import base64
import quopri
import re
import os
from typing import Dict, List, Optional
from email import message_from_bytes
from email.utils import getaddresses

# Directory to save images
IMAGE_DIR = "/path/to/save/images/"  # Change to your desired image save directory


# Helper function to save images
def save_image(content, filename):
    file_path = os.path.join(IMAGE_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def _b64url_decode(s: Optional[str]) -> str:
    if not s:
        return ""
    # Gmail uses URL-safe base64 without padding
    padding = "=" * (-len(s) % 4)
    raw = base64.urlsafe_b64decode(s + padding)
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return raw.decode("latin-1", errors="replace")


def _maybe_qp_decode(s: str, content_transfer_encoding: Optional[str]) -> str:
    if not s:
        return ""
    if content_transfer_encoding and content_transfer_encoding.lower() == "quoted-printable":
        try:
            return quopri.decodestring(s).decode("utf-8", errors="replace")
        except Exception:
            return quopri.decodestring(s).decode("latin-1", errors="replace")
    return s


def _get_header(headers: List[Dict], name: str) -> Optional[str]:
    for h in headers or []:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


def _walk_parts_collect(payload: Dict, out: Dict):
    """
    Recursively walk Gmail payload to collect best text/plain and text/html.
    """
    if not payload:
        return

    mime = payload.get("mimeType", "")
    body = payload.get("body", {}) or {}
    data = body.get("data")
    headers = payload.get("headers", []) or []
    cte = _get_header(headers, "Content-Transfer-Encoding")

    # If this node has content
    if data:
        decoded = _b64url_decode(data)
        decoded = _maybe_qp_decode(decoded, cte)

        if mime.startswith("text/plain"):
            # prefer the longest plain text we find
            if len(decoded) > len(out.get("text", "")):
                out["text"] = decoded
        elif mime.startswith("text/html"):
            if len(decoded) > len(out.get("html", "")):
                out["html"] = decoded

    # If this node has children, recurse
    for part in payload.get("parts", []) or []:
        _walk_parts_collect(part, out)


def _html_to_text(html: str) -> str:
    # very light HTML -> text fallback (you can swap for bleach or bs4 later)
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n\n", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_images_from_email(raw_email):
    msg = message_from_bytes(raw_email)
    image_files = []

    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition"))

        # Check for inline images
        if "image" in content_type and "attachment" not in content_disposition:
            content_id = part.get("Content-ID")  # Look for Content-ID in case it's an inline image
            content_type = part.get_content_type()
            content_transfer_encoding = part.get("Content-Transfer-Encoding")

            image_data = part.get_payload(decode=True)

            # Get the filename for saving the image
            filename = part.get_filename()
            if not filename:
                filename = f"{content_id}.jpg"  # Fallback if filename is not present

            # Save the image
            saved_image_path = save_image(image_data, filename)
            image_files.append(saved_image_path)

    return image_files


def parse_message(message: Dict) -> Dict:
    """
    Returns:
      {
        'sender': str|None,
        'subject': str|None,
        'thread_id': str|None,
        'message_id': str|None,
        'text': full_text_body (best-effort),
        'html': full_html_body (if available),
        'images': List of image file paths
      }
    """
    payload = message.get("payload", {}) or {}
    headers = payload.get("headers", []) or []

    sender = _get_header(headers, "From")
    subject = _get_header(headers, "Subject")
    thread_id = message.get("threadId")
    message_id = message.get("id")

    out = {"text": "", "html": ""}
    # Walk tree to fill text/html
    _walk_parts_collect(payload, out)

    # Extract inline images and save them
    image_files = extract_images_from_email(payload)

    # Some messages are not multipart and store body at top-level payload.body.data
    if not out["text"] and not out["html"]:
        body_data = payload.get("body", {}).get("data")
        if body_data:
            # choose based on mimeType
            decoded = _b64url_decode(body_data)
            cte = _get_header(headers, "Content-Transfer-Encoding")
            decoded = _maybe_qp_decode(decoded, cte)
            if (payload.get("mimeType") or "").startswith("text/html"):
                out["html"] = decoded
            else:
                out["text"] = decoded

    # If still no text but we have HTML, produce a plain-text fallback
    if not out["text"] and out["html"]:
        out["text"] = _html_to_text(out["html"])

    return {
        "sender": sender,
        "subject": subject,
        "thread_id": thread_id,
        "message_id": message_id,
        "text": out["text"] or "",
        "html": out["html"] or "",
        "images": image_files
    }
