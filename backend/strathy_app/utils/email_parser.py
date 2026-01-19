import base64
import re
from html.parser import HTMLParser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def _b64url_decode(data: str) -> bytes:
    """Decode base64url with padding fix."""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def get_header(headers, name):
    """Get a specific header value (case-insensitive)."""
    for h in headers or []:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


class _HTMLToText(HTMLParser):
    """Very small HTML → plaintext converter (links preserved as text)."""

    def __init__(self):
        super().__init__()
        self._chunks = []

    def handle_data(self, data):
        self._chunks.append(data)

    def handle_entityref(self, name):
        # HTMLParser.unescape is deprecated in newer Python,
        # but leaving this pattern because it's already in your codebase.
        self._chunks.append(self.unescape(f"&{name};"))

    def handle_charref(self, name):
        self._chunks.append(self.unescape(f"&#{name};"))

    def get_text(self):
        text = "".join(self._chunks)
        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def _html_to_text(html: str) -> str:
    parser = _HTMLToText()
    parser.feed(html or "")
    return parser.get_text()


def _extract_body_from_part(part) -> tuple[str, bool]:
    """Extract text or HTML from MIME parts."""
    mime = (part.get("mimeType") or "").lower()
    body = part.get("body", {}) or {}
    data = body.get("data")

    if data:
        decoded = _b64url_decode(data).decode("utf-8", errors="replace")
        if mime == "text/plain":
            return decoded, True
        if mime == "text/html":
            return _html_to_text(decoded), False
    return "", False


def _walk_parts(payload) -> str:
    """Recursively find text/plain or fallback to text/html."""
    if not payload:
        return ""
    parts = payload.get("parts") or []
    if not parts:
        text, _is_plain = _extract_body_from_part(payload)
        return text

    found_html = None
    for part in parts:
        mime = (part.get("mimeType") or "").lower()
        if mime.startswith("multipart/"):
            text = _walk_parts(part)
            if text:
                return text
        else:
            text, is_plain = _extract_body_from_part(part)
            if is_plain and text:
                return text
            if not is_plain and text and found_html is None:
                found_html = text
    return found_html or ""


def _relative_time(dt: datetime) -> str:
    """Return human-friendly relative time like '2 hours ago'."""
    if not dt:
        return ""
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        m = seconds // 60
        return f"{m} minute{'s' if m != 1 else ''} ago"
    elif seconds < 86400:
        h = seconds // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    elif seconds < 604800:
        d = seconds // 86400
        return f"{d} day{'s' if d != 1 else ''} ago"
    else:
        return dt.strftime("%b %d, %Y")


# ==========================
# NEW: reply/quote cleaner
# ==========================

# Common reply separators (Gmail, Outlook, some clients)
_REPLY_CUTOFF_PATTERNS = [
    r"\nOn .+ wrote:\n",          # Gmail: "On Mon, ... wrote:"
    r"\nFrom:\s.*\n",             # Outlook-ish
    r"\nSent:\s.*\n",
    r"\nTo:\s.*\n",
    r"\nSubject:\s.*\n",
]

# Footer/disclaimer patterns (you can add more as you see them)
_DISCLAIMER_PATTERNS = [
    r"Note:\s*All emails sent from Strathmore University.*",  # your footer block
    r"All emails sent from Strathmore University.*",
    r"Visit our Facebook.*",
    r"\"Visit our Facebook.*",
    r"http://www\.strathmore\.edu/en/email-policy.*",
    r"www\.strathmore\.edu/en/email-policy.*",
]


def clean_reply_text(body: str) -> str:
    """
    Removes quoted history and footers so we keep only the new reply text.
    Works best on plain text (Gmail typically sends that on replies).
    """
    if not body:
        return ""

    text = body.replace("\r\n", "\n").replace("\r", "\n").strip()

    # 1) Cut off at common reply markers
    for pattern in _REPLY_CUTOFF_PATTERNS:
        parts = re.split(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if parts and len(parts) > 1:
            text = parts[0].strip()

    # 2) Drop quoted lines beginning with ">"
    lines = []
    for line in text.splitlines():
        if line.strip().startswith(">"):
            continue
        lines.append(line)
    text = "\n".join(lines).strip()

    # 3) Remove common signature/footer blocks
    for pat in _DISCLAIMER_PATTERNS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE | re.DOTALL).strip()

    # 4) Collapse excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text


def parse_message(message):
    """
    Given Gmail message JSON, return dict with:
        sender, subject, body, thread_id, message_id, date, relative_time

    NOTE:
    body is cleaned (reply history + footers removed) to behave like chat input.
    """
    payload = message.get("payload", {}) or {}
    headers = payload.get("headers", []) or []

    sender = get_header(headers, "From")
    subject = get_header(headers, "Subject")

    # Handle Date (various header casing possibilities)
    date_str = (
        get_header(headers, "Date")
        or get_header(headers, "date")
        or get_header(headers, "Sent")
        or get_header(headers, "Received")
    )

    thread_id = message.get("threadId")
    message_id = message.get("id")

    # Parse email date robustly
    parsed_dt = None
    formatted_date = None
    relative = None
    if date_str:
        try:
            parsed_dt = parsedate_to_datetime(date_str)
            if parsed_dt.tzinfo is None:
                parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
            formatted_date = parsed_dt.isoformat()
            relative = _relative_time(parsed_dt)
        except Exception:
            formatted_date = date_str

    # Get body text
    body = _walk_parts(payload)
    if not body:
        data = (payload.get("body") or {}).get("data")
        if data:
            body = _b64url_decode(data).decode("utf-8", errors="replace")

    # ✅ NEW: clean quoted reply + footer noise
    cleaned_body = clean_reply_text(body or "")

    return {
        "sender": sender,
        "subject": subject,
        "body": cleaned_body,  # <-- IMPORTANT: return cleaned body
        "thread_id": thread_id,
        "message_id": message_id,
        "date": formatted_date,
        "relative_time": relative or "unknown time",
    }
