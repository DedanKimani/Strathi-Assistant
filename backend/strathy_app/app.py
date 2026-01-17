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
from backend.strathy_app.models.models import Student, Conversation, SessionLocal  # ✅ Make sure this import is present
from backend.strathy_app.services.student_service import create_or_update_student

from backend.strathy_app.services.model_extraction_service import extract_student_details  # create this
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from fastapi import Depends

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
    extract_thread_messages,

)
from .utils.email_parser import parse_message
from .utils.mime_helpers import build_reply_mime

# Import the synchronous extraction helper at the top
from backend.strathy_app.services.model_extraction_service import extract_student_details
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from fastapi import Depends



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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ====== Main Inbox Route ======
@app.get("/gmail/unread")
def gmail_unread(db: Session = Depends(get_db)):
    creds = _load_creds()
    if not creds:
        return JSONResponse({"ok": False, "message": "Not logged in"}, status_code=401)

    service = build_gmail_service(creds)
    msgs = list_unread_messages(service, max_results=100)

    # ✅ NEW: group unread messages by Gmail threadId
    latest_by_thread = {}  # threadId -> {"full": msg_json, "parsed": parsed, "ts": int}

    for m in msgs:
        full = get_message(service, m["id"])
        if not full:
            continue

        parsed = parse_message(full)
        thread_id = full.get("threadId") or parsed.get("thread_id")
        if not thread_id:
            continue

        ts = int(full.get("internalDate", "0") or 0)

        # Keep the latest unread message per thread as the preview
        if thread_id not in latest_by_thread or ts > latest_by_thread[thread_id]["ts"]:
            latest_by_thread[thread_id] = {"full": full, "parsed": parsed, "ts": ts}

    previews = []

    for thread_id, item in latest_by_thread.items():
        full = item["full"]
        parsed = item["parsed"]

        sender_email = (parsed.get("sender") or "").split("<")[-1].strip(">").lower()

        conversation = db.query(Conversation).filter(Conversation.thread_id == thread_id).first()
        student = (
            db.query(Student).filter(Student.id == conversation.student_id).first()
            if conversation and conversation.student_id
            else None
        )

        # ✅ Save/update conversation preview (latest body/subject)
        if not conversation:
            conversation = Conversation(
                student_id=student.id if student else None,
                thread_id=thread_id,
                subject=parsed.get("subject"),
                message_body=parsed.get("body") or "",
            )
            db.add(conversation)
        else:
            conversation.subject = parsed.get("subject") or conversation.subject
            conversation.message_body = parsed.get("body") or conversation.message_body
        db.commit()

        extracted = None
        if conversation and conversation.message_body and conversation.details_status in [None, "", "empty"]:
            try:
                extracted = extract_student_details(conversation.message_body)
                conversation.full_thread_summary = extracted.get("full_thread_summary", "")
                conversation.details_status = extracted.get("details_status", "empty")
                conversation.missing_fields = extracted.get("missing_fields", [])
                conversation.follow_up_message = extracted.get("follow_up_message", "")

                if not student and extracted.get("admission_number"):
                    student_payload = {
                        "full_name": extracted.get("full_name"),
                        "admission_number": extracted.get("admission_number"),
                        "course": extracted.get("course"),
                        "year": extracted.get("year"),
                        "semester": extracted.get("semester"),
                        "group": extracted.get("group"),
                        "email": sender_email,
                    }
                    student = create_or_update_student(db, student_payload)
                    conversation.student_id = student.id

                db.commit()
            except Exception as e:
                print(f"⚠️ Extraction failed for conversation {conversation.id}: {e}")

        # ✅ OPTIONAL but helpful: include full thread history for chat UI
        thread_messages = extract_thread_messages(service, thread_id)

        previews.append({
            "id": parsed.get("message_id"),
            "threadId": thread_id,
            "from": parsed.get("sender"),
            "student_email": student.email if student else sender_email,
            "student_name": student.full_name if student else (extracted.get("full_name") if extracted else ""),
            "admission_number": student.admission_number if student else (extracted.get("admission_number") if extracted else ""),
            "course": student.course if student else (extracted.get("course") if extracted else ""),
            "year": student.year if student else (extracted.get("year") if extracted else ""),
            "semester": student.semester if student else (extracted.get("semester") if extracted else ""),
            "group": student.group if student else (extracted.get("group") if extracted else ""),
            "subject": parsed.get("subject"),
            "student_query": parsed.get("body") or "",
            "full_thread_summary": conversation.full_thread_summary if conversation else "",
            "details_status": conversation.details_status if conversation else "empty",
            "missing_fields": conversation.missing_fields if conversation else [],
            "follow_up_message": conversation.follow_up_message if conversation else "",
            "thread_messages": thread_messages,  # ✅ the continuous back-and-forth
        })

    # Sort previews by latest timestamp (newest first)
    previews.sort(key=lambda x: latest_by_thread.get(x["threadId"], {}).get("ts", 0), reverse=True)

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
    if not result:
        return {"ok": False, "message": "No AI reply generated"}

    # === Fetch student details ===
    db = SessionLocal()
    student_id = result.get("student_id")
    student = db.query(Student).filter(Student.id == student_id).first() if student_id else None
    db.close()

    student_data = None
    if student:
        student_data = {
            "full_name": student.full_name,
            "admission_number": student.admission_number,
            "course": student.course,
            "year": student.year,
            "semester": student.semester,
            "group": student.group,
        }

    return {
        "ok": True,
        "subject": result["subject"],
        "student_query": result.get("body", ""),
        "ai_reply": result.get("ai_reply", ""),
        "role": result["role"],
        "status": result.get("status"),
        "received_at": result.get("received_at"),
        "student_details": student_data,
    }

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

# ====== Student Details Extraction (Claude) ======
from pydantic import BaseModel
from anthropic import Anthropic
import json

anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


class EmailBody(BaseModel):
    body_text: str


# ===== Student Details Endpoint =====
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import func  # ✅ For case-insensitive email matching


# ===== Database Session Dependency =====
def get_db():
    """
    Creates and cleans up a database session for each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===== Get Student by Email =====
@app.get("/students/{email}")
def get_student_by_email(email: str, db: Session = Depends(get_db)):
    normalized_email = email.strip().lower()
    student = db.query(Student).filter(func.lower(Student.email) == normalized_email).first()
    if not student:
        return JSONResponse({"ok": False, "error": "Student not found", "email": normalized_email}, status_code=404)

    conversations = (
        db.query(Conversation)
        .filter(Conversation.student_id == student.id)
        .order_by(Conversation.last_updated.desc())
        .all()
    )

    convo_data = []
    for c in conversations:
        # Extract details if message_body exists and details are empty
        if c.message_body and c.details_status in [None, "", "empty"]:
            try:
                extracted = extract_student_details(c.message_body)  # ✅ synchronous helper
                c.full_thread_summary = extracted.get("full_thread_summary", "")
                c.details_status = extracted.get("details_status", "empty")
                c.missing_fields = extracted.get("missing_fields", [])
                c.follow_up_message = extracted.get("follow_up_message", "")
                db.commit()
            except Exception as e:
                print(f"⚠️ Extraction failed for conversation {c.id}: {e}")

        convo_data.append({
            "id": c.id,
            "thread_id": c.thread_id,
            "subject": c.subject,
            "full_thread_summary": c.full_thread_summary,
            "details_status": c.details_status,
            "missing_fields": c.missing_fields,
            "follow_up_message": c.follow_up_message,
            "last_updated": c.last_updated,
        })

    return {
        "ok": True,
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "email": student.email,
            "admission_number": student.admission_number,
            "course": student.course,
            "year": student.year,
            "semester": student.semester,
            "group": student.group,
            "created_at": student.created_at,
        },
        "conversations": convo_data,
    }
