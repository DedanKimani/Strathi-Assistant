import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from pathlib import Path
from typing import Optional
import logging

from fastapi import FastAPI, Request, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from apscheduler.schedulers.background import BackgroundScheduler

from .config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE
from .services.gmail_service import (
    build_gmail_service,
    list_unread_messages,
    get_message,
    send_mime,
    process_incoming_email,
    get_ai_reply_for_thread,
    is_sender_allowed,
)
from .utils.email_parser import parse_message
from .utils.mime_helpers import build_reply_mime


# ====== Setup ======
load_dotenv()
logging.basicConfig(level=logging.INFO)

# ====== FastAPI App ======
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-to-a-long-random-string")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# ====== CORS ======
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== Token Management ======
def _save_creds(creds: Credentials):
    Path(TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")


def _load_creds() -> Optional[Credentials]:
    if not Path(TOKEN_FILE).exists():
        return None
    try:
        return Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    except Exception:
        return None


# ====== Routes ======
@app.get("/")
def index():
    return {"ok": True, "message": "Strathy Gmail Automation API is running."}


@app.get("/oauth2/login")
def auth_login(request: Request):
    redirect_uri = f"{BASE_URL}/oauth2callback"
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["oauth_state"] = state
    return RedirectResponse(authorization_url)


@app.get("/oauth2callback")
def auth_callback(request: Request):
    expected_state = request.session.get("oauth_state")
    returned_state = request.query_params.get("state")

    if not expected_state or expected_state != returned_state:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "State mismatch. Please retry login."},
        )

    redirect_uri = f"{BASE_URL}/oauth2callback"
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        state=expected_state,
        redirect_uri=redirect_uri,
    )

    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials
    _save_creds(creds)
    request.session.pop("oauth_state", None)
    return RedirectResponse(url="/gmail/unread")


# ====== Main Inbox Route ======
@app.get("/gmail/unread")
def gmail_unread():
    creds = _load_creds()
    if not creds:
        return JSONResponse({"ok": False, "message": "Not logged in"}, status_code=401)

    service = build_gmail_service(creds)
    msgs = list_unread_messages(service, max_results=100)
    previews = []

    for m in msgs:
        full = get_message(service, m["id"])
        if not full:
            continue

        parsed = parse_message(full)
        thread_id = parsed.get("thread_id")
        sender = parsed.get("sender") or ""
        sender_email = sender.split("<")[-1].strip(">").lower()
        ai_reply = get_ai_reply_for_thread(service, thread_id)

        # Determine sender permission
        allowed = is_sender_allowed(sender_email)

        # Assign correct status
        if not allowed:
            status = "blocked"
            ai_reply = None
        else:
            status = "replied" if ai_reply else "pending"

        previews.append({
            "id": parsed.get("message_id"),
            "threadId": thread_id,
            "from": sender,
            "subject": parsed.get("subject"),
            "student_query": parsed.get("body") or "",
            "ai_reply": ai_reply,
            "role": "student",
            "status": status,
            "date": parsed.get("date"),
            "relative_time": parsed.get("relative_time") or "unknown time"
        })

    return JSONResponse(previews)


@app.get("/gmail/last-reply")
def gmail_last_reply():
    creds = _load_creds()
    if not creds:
        return JSONResponse({"ok": False, "message": "Not logged in"}, status_code=401)

    service = build_gmail_service(creds)
    unread = list_unread_messages(service, max_results=1)
    if not unread:
        return {"ok": False, "message": "No unread messages found"}

    msg = unread[0]
    result = process_incoming_email(service, msg)
    if result:
        return {
            "ok": True,
            "subject": result["subject"],
            "student_query": result.get("body", ""),
            "ai_reply": result.get("ai_reply", ""),
            "role": result["role"],
            "status": result.get("status"),
            "received_at": result.get("received_at"),
        }

    return {"ok": False, "message": "No AI reply generated"}


@app.post("/gmail/reply")
def gmail_reply(message_id: str = Body(..., embed=True), body_text: str = Body(..., embed=True)):
    creds = _load_creds()
    if not creds:
        return JSONResponse({"ok": False, "error": "Not logged in"}, status_code=401)

    service = build_gmail_service(creds)
    original = get_message(service, message_id)
    if not original:
        return JSONResponse({"ok": False, "error": "Original message not found"}, status_code=404)

    parsed = parse_message(original)
    to_email = (parsed.get("sender") or "").split("<")[-1].strip(">").lower()

    if not is_sender_allowed(to_email):
        return JSONResponse(
            status_code=403,
            content={"ok": False, "error": f"Sending to {to_email} is not allowed."},
        )

    subject = parsed.get("subject") or "(no subject)"
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    raw_mime = build_reply_mime(
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        in_reply_to=original.get("payload", {}).get("headers", []),
        original_headers=original.get("payload", {}).get("headers", []),
    )

    sent = send_mime(service, raw_mime, thread_id=parsed["thread_id"])
    return JSONResponse({
        "ok": True,
        "sent_id": sent.get("id"),
        "threadId": sent.get("threadId"),
        "status": "replied"
    })


# ===== Auto Reply Job =====
def auto_reply_job():
    creds = _load_creds()
    if not creds:
        logging.info("No creds available yet. Skipping auto-reply job.")
        return

    try:
        service = build_gmail_service(creds)
        unread = list_unread_messages(service, max_results=1)
        if not unread:
            logging.info("No unread messages found.")
            return

        first_msg = unread[0]
        full = get_message(service, first_msg["id"])
        parsed = parse_message(full)
        sender = parsed.get("sender") or ""
        sender_email = sender.split("<")[-1].strip(">").lower()

        if not is_sender_allowed(sender_email):
            logging.info(f"⛔ Skipping auto-reply for blocked/disallowed sender: {sender_email}")
            return

        result = process_incoming_email(service, first_msg)
        if result:
            logging.info(f"✅ Auto-replied to {result.get('from')} | Subject: {result.get('subject')}")

    except Exception as e:
        logging.error(f"Auto-reply job failed: {e}")


# ====== Scheduler ======
scheduler = BackgroundScheduler()
scheduler.add_job(auto_reply_job, "interval", minutes=3)
scheduler.start()
