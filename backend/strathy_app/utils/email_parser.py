import base64
import re
from html.parser import HTMLParser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

def _b64url_decode(data: str) -> bytes:
    """Decode base64url with padding fix."""
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)

def get_header(headers, name):
    """Get a specific header value (case-insensitive)."""
    for h in headers or []:
        if h.get('name', '').lower() == name.lower():
            return h.get('value')
    return None

class _HTMLToText(HTMLParser):
    """Very small HTML → plaintext converter (links preserved as text)."""
    def __init__(self):
        super().__init__()
        self._chunks = []

    def handle_data(self, data):
        self._chunks.append(data)

    def handle_entityref(self, name):
        self._chunks.append(self.unescape(f"&{name};"))

    def handle_charref(self, name):
        self._chunks.append(self.unescape(f"&#{name};"))

    def get_text(self):
        text = ''.join(self._chunks)
        text = re.sub(r'\s+\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

def _html_to_text(html: str) -> str:
    parser = _HTMLToText()
    parser.feed(html or "")
    return parser.get_text()

def _extract_body_from_part(part) -> tuple[str, bool]:
    """Extract text or HTML from MIME parts."""
    mime = (part.get('mimeType') or '').lower()
    body = part.get('body', {}) or {}
    data = body.get('data')

    if data:
        decoded = _b64url_decode(data).decode('utf-8', errors='replace')
        if mime == 'text/plain':
            return decoded, True
        if mime == 'text/html':
            return _html_to_text(decoded), False
    return "", False

def _walk_parts(payload) -> str:
    """Recursively find text/plain or fallback to text/html."""
    if not payload:
        return ""
    parts = payload.get('parts') or []
    if not parts:
        text, is_plain = _extract_body_from_part(payload)
        return text

    found_html = None
    for part in parts:
        mime = (part.get('mimeType') or '').lower()
        if mime.startswith('multipart/'):
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

def parse_message(message):
    """
    Given Gmail message JSON, return dict with:
        sender, subject, body, thread_id, message_id, date, relative_time
    """
    payload = message.get('payload', {}) or {}
    headers = payload.get('headers', []) or []

    sender = get_header(headers, 'From')
    subject = get_header(headers, 'Subject')

    # Handle Date (various header casing possibilities)
    date_str = (
        get_header(headers, 'Date')
        or get_header(headers, 'date')
        or get_header(headers, 'Sent')
        or get_header(headers, 'Received')
    )

    thread_id = message.get('threadId')
    message_id = message.get('id')

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
        data = (payload.get('body') or {}).get('data')
        if data:
            body = _b64url_decode(data).decode('utf-8', errors='replace')

    return {
        'sender': sender,
        'subject': subject,
        'body': body or "",
        'thread_id': thread_id,
        'message_id': message_id,
        'date': formatted_date,
        'relative_time': relative or "unknown time"
    }
