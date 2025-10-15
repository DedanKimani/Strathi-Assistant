# backend/strathy_app/services/conversation_service.py

from sqlalchemy.orm import Session
from datetime import datetime
from backend.strathy_app.models.models import Conversation, Message
from .student_service import create_or_update_student
from backend.strathy_app.services.model_extraction_service import extract_student_details


def save_conversation_and_messages(db: Session, email_text: str, subject: str, sender_email: str, thread_id: str):
    """
    1. Extracts student details from email_text.
    2. Creates or updates the student (now includes full_thread_summary).
    3. Saves the conversation and message to the DB.
    """

    # 🔍 Extract student details from the message using your AI model
    extracted = extract_student_details(email_text)

    # Construct student data payload for DB
    student_data = {
        "full_name": extracted.get("full_name"),
        "admission_number": extracted.get("admission_number"),
        "course": extracted.get("course"),
        "year": extracted.get("year"),
        "semester": extracted.get("semester"),
        "group": extracted.get("group"),
        "email": sender_email,
        # 🆕 Add AI-generated summary of the full thread/message
        "full_thread_summary": extracted.get("message_summary"),
    }

    # 🏫 Create or update the student record
    student = create_or_update_student(db, student_data)

    # 🎯 Check if conversation already exists
    convo = (
        db.query(Conversation)
        .filter(Conversation.thread_id == thread_id)
        .first()
    )

    if not convo:
        convo = Conversation(
            thread_id=thread_id,
            student_id=student.id,
            subject=subject,
            last_updated=datetime.utcnow(),
        )
        db.add(convo)
        db.commit()
        db.refresh(convo)
    else:
        convo.last_updated = datetime.utcnow()
        db.commit()

    # 💬 Save the message itself
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

    # ✅ Return everything for logging or frontend use
    return {
        "student": student,
        "conversation": convo,
        "message": new_msg,
        "extracted": extracted,
    }
