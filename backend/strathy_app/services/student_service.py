# backend/strathy_app/services/student_service.py

from sqlalchemy.orm import Session
from backend.strathy_app.models.models import Student, Conversation
import json

def get_student_by_email(db: Session, email: str):
    return db.query(Student).filter(Student.email == email).first()


def create_or_update_student(db: Session, data: dict, thread_id: str = None):
    """
    Create or update a student record.
    Expected keys: full_name, admission_number, course, year, semester, group, email
    Conversation-related keys (details_status, missing_fields, follow_up_message, full_thread_summary)
    are now handled separately per conversation.
    """
    if not data.get("email"):
        raise ValueError("Email is required")

    student = get_student_by_email(db, data["email"])

    # Normalize missing_fields if provided as list or JSON string
    if "missing_fields" in data and data["missing_fields"] is not None:
        mf = data["missing_fields"]
        if isinstance(mf, str):
            try:
                data["missing_fields"] = json.loads(mf)
            except Exception:
                data["missing_fields"] = [mf]
        elif not isinstance(mf, (list, dict)):
            data["missing_fields"] = [mf]

    # --- Handle Student fields only ---
    student_fields = {
        "full_name",
        "admission_number",
        "course",
        "year",
        "semester",
        "group",
        "email",
    }

    student_data = {k: v for k, v in data.items() if k in student_fields}

    if student:
        for key, value in student_data.items():
            if value is not None:
                setattr(student, key, value)
    else:
        student = Student(**student_data)
        db.add(student)
        db.commit()
        db.refresh(student)

    # --- Handle Conversation fields if thread_id provided ---
    if thread_id:
        convo_fields = {
            "details_status",
            "missing_fields",
            "follow_up_message",
            "full_thread_summary",
        }

        convo_data = {k: v for k, v in data.items() if k in convo_fields}

        if convo_data:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.thread_id == thread_id)
                .first()
            )

            if not conversation:
                conversation = Conversation(
                    student_id=student.id,
                    thread_id=thread_id,
                )
                db.add(conversation)

            for key, value in convo_data.items():
                if value is not None:
                    setattr(conversation, key, value)

    db.commit()
    db.refresh(student)
    return student
