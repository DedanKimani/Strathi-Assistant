# backend/strathy_app/services/gmail_service.py
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE

def build_gmail_service(creds: Credentials):
    """Load/refresh creds and return a Gmail service client."""
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)

def list_unread_messages(service, q: str = "is:unread", max_results: int = 5) -> List[Dict]:
    try:
        resp = service.users().messages().list(
            userId="me", q=q, labelIds=["INBOX"], maxResults=max_results
        ).execute()
        return resp.get("messages", [])
    except HttpError as e:
        print(f"Error listing messages: {e}")
        return []

def get_message(service, message_id: str, fmt: str = "full") -> Optional[Dict]:
    try:
        return service.users().messages().get(userId="me", id=message_id, format=fmt).execute()
    except HttpError as e:
        print(f"Error getting message {message_id}: {e}")
        return None

def send_mime(service, raw_b64url: str, thread_id: Optional[str] = None) -> Dict:
    """Send a base64url-encoded RFC-2822 MIME string via Gmail API."""
    body = {"raw": raw_b64url}
    if thread_id:
        body["threadId"] = thread_id
    try:
        return service.users().messages().send(userId="me", body=body).execute()
    except HttpError as e:
        raise RuntimeError(f"Gmail send failed: {e}") from e
