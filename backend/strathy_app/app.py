# backend/strathy_app/app.py
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from .config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE
from .services.gmail_service import (
    build_gmail_service,
    list_unread_messages,
    get_message,
    send_mime,
)
from .utils.email_parser import parse_message
from .utils.mime_helpers import build_reply_mime


load_dotenv()

# IMPORTANT: keep SECRET_KEY constant across restarts/workers
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-to-a-long-random-string")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")  # exact domain for callback

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

def _save_creds(creds: Credentials):
    Path(TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")

def _load_creds() -> Optional[Credentials]:
    if not Path(TOKEN_FILE).exists():
        return None
    try:
        return Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    except Exception:
        return None

@app.get("/")
def index():
    return {"ok": True, "message": "Strathy OAuth demo. Visit /oauth2/login to begin."}

# ===== OAuth: Login → Google consent =====
@app.get("/oauth2/login")
def auth_login(request: Request):
    redirect_uri = f"{BASE_URL}/oauth2callback"  # must match Google Console redirect
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # ensures refresh_token first time
    )
    request.session["oauth_state"] = state
    return RedirectResponse(authorization_url)

# ===== OAuth: Callback from Google =====
@app.get("/oauth2callback")
def auth_callback(request: Request):
    expected_state = request.session.get("oauth_state")
    returned_state = request.query_params.get("state")
    if not expected_state or expected_state != returned_state:
        raise HTTPException(status_code=400, detail="State mismatch. Please retry login.")

    redirect_uri = f"{BASE_URL}/oauth2callback"
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        state=expected_state,
        redirect_uri=redirect_uri,
    )

    authorization_response = str(request.url)  # full URL with code & state
    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials
    _save_creds(creds)
    request.session.pop("oauth_state", None)
    return RedirectResponse(url="/gmail/unread")

# ===== Demo: list a few unread messages =====
@app.get("/gmail/unread")
def gmail_unread():
    creds = _load_creds()
    if not creds:
        return RedirectResponse("/oauth2/login")
    service = build_gmail_service(creds)
    msgs = list_unread_messages(service, max_results=5)
    # Fetch a short preview for convenience
    previews = []
    for m in msgs:
        full = get_message(service, m["id"])
        if not full:
            continue
        parsed = parse_message(full)
        previews.append({
            "id": parsed["message_id"],
            "threadId": parsed["thread_id"],
            "from": parsed["sender"],
            "subject": parsed["subject"],
            "body_preview": (parsed["body"] or "")[:200],
        })
    return JSONResponse(previews)

# ===== Demo: reply to a message =====
@app.post("/gmail/reply")
def gmail_reply(
    message_id: str = Body(..., embed=True),
    body_text: str = Body(..., embed=True),
):
    """
    Example JSON:
    {
      "message_id": "185f0a...abc",
      "body_text": "Hi! Thanks for reaching out..."
    }
    """
    creds = _load_creds()
    if not creds:
        return RedirectResponse("/oauth2/login")
    service = build_gmail_service(creds)

    # Get original message to extract headers/thread
    original = get_message(service, message_id)
    if not original:
        raise HTTPException(status_code=404, detail="Original message not found")

    # Parse for headers and thread info
    parsed = parse_message(original)
    thread_id = parsed["thread_id"]
    # "From" contains display name + email; we reply to the email address
    to_email = (parsed["sender"] or "").split("<")[-1].strip(">")
    subject = parsed["subject"] or "(no subject)"
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    # Build RFC-2822 MIME reply (+ In-Reply-To / References)
    raw_mime = build_reply_mime(
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        in_reply_to=original.get("payload", {}).get("headers", []),
        original_headers=original.get("payload", {}).get("headers", []),
    )

    # Send using messages.send with threadId to keep it in the same thread
    sent = send_mime(service, raw_mime, thread_id=thread_id)

    return JSONResponse({"ok": True, "sent_id": sent.get("id"), "threadId": sent.get("threadId")})
