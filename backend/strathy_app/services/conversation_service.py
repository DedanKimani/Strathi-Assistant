# backend/strathy_app/services/conversation_service.py

from sqlalchemy.orm import Session
from datetime import datetime
from backend.strathy_app.models.models import Conversation, Message
from .student_service import create_or_update_student
from backend.strathy_app.services.model_extraction_service import extract_student_details


def save_conversation_and_messages(db: Session, email_text: str, subject: str, sender_email: str, thread_id: str):
    """
    Extracts student details, saves/updates the student, and stores
    thread-specific info (summary, missing fields, follow-up) in the Conversation table.
    """

    # 🔍 Extract structured info from message text
    extracted = extract_student_details(email_text) or {}

    # 🧠 Student-level data (stable identity info)
    student_data = {
        "full_name": extracted.get("full_name"),
        "admission_number": extracted.get("admission_number"),
        "course": extracted.get("course"),
        "year": extracted.get("year"),
        "semester": extracted.get("semester"),
        "group": extracted.get("group"),
        "email": sender_email,
    }

    # 🏫 Create or update Student record
    student = create_or_update_student(db, student_data, thread_id=thread_id)

    # 🎯 Find or create Conversation record (thread-level)
    convo = (
        db.query(Conversation)
        .filter(Conversation.thread_id == thread_id)
        .first()
    )

    # Extract per-thread fields (defaults ensure data safety)
    full_thread_summary = extracted.get("full_thread_summary") or ""
    details_status = extracted.get("details_status") or "empty"
    missing_fields = extracted.get("missing_fields") or []
    follow_up_message = extracted.get("follow_up_message") or ""

    if not convo:
        convo = Conversation(
            thread_id=thread_id,
            student_id=student.id,
            subject=subject,
            last_updated=datetime.utcnow(),
            full_thread_summary=full_thread_summary,
            details_status=details_status,
            missing_fields=missing_fields,
            follow_up_message=follow_up_message,
        )
        db.add(convo)
    else:
        # 🧩 Only update fields if new data is available
        convo.last_updated = datetime.utcnow()
        convo.full_thread_summary = full_thread_summary or convo.full_thread_summary
        convo.details_status = details_status or convo.details_status
        convo.missing_fields = missing_fields or convo.missing_fields
        convo.follow_up_message = follow_up_message or convo.follow_up_message

    db.commit()
    db.refresh(convo)

    # 💬 Store the actual message content
    new_msg = Message(
        message_id=f"{thread_id}-{datetime.utcnow().timestamp()}",
        conversation_id=convo.id,
        sender_email=sender_email,
        sender_name=extracted.get("full_name") or "Unknown",
        subject=subject,
        body=email_text,
        role="student",
        sent_at=datetime.utcnow(),
    )

    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    return {
        "student": student,
        "conversation": convo,
        "message": new_msg,
        "extracted": extracted,
    }
