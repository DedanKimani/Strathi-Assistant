import base64
import re
from html.parser import HTMLParser

def _b64url_decode(data: str) -> bytes:
    # Add missing padding if necessary
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)

def get_header(headers, name):
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
        # Collapse whitespace a bit
        text = re.sub(r'\s+\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

def _html_to_text(html: str) -> str:
    parser = _HTMLToText()
    parser.feed(html or "")
    return parser.get_text()

def _extract_body_from_part(part) -> tuple[str, bool]:
    """
    Returns (text, found_plain) where found_plain indicates if this is text/plain.
    Falls back to text/html if plain missing.
    """
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
    """
    Depth-first search for text/plain; if none, use first text/html.
    """
    if not payload:
        return ""

    parts = payload.get('parts') or []
    # Single-part (no 'parts')—try direct body
    if not parts:
        text, is_plain = _extract_body_from_part(payload)
        return text

    found_html = None
    # Prefer text/plain anywhere in the tree
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

def parse_message(message):
    """
    Given Gmail message JSON, return dict with:
        sender, subject, body, thread_id, message_id
    """
    payload = message.get('payload', {}) or {}
    headers = payload.get('headers', []) or []

    sender = get_header(headers, 'From')
    subject = get_header(headers, 'Subject')
    thread_id = message.get('threadId')
    message_id = message.get('id')

    # Try to extract body from multipart; fallback to single-part body
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
        'message_id': message_id
    }