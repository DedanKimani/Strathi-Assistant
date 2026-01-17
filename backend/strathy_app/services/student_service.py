# backend/strathy_app/services/student_service.py

from sqlalchemy.orm import Session
from backend.strathy_app.models.models import Student, Conversation
import json

def get_student_by_email(db: Session, email: str):
    return db.query(Student).filter(Student.email == email).first()

def get_student_by_admission_number(db: Session, admission_number: str):
    return (
        db.query(Student)
        .filter(Student.admission_number == admission_number)
        .first()
    )
def create_or_update_student(db: Session, data: dict, thread_id: str = None):
    """
    Create or update a student record.
    Expected keys: full_name, admission_number, course, year, semester, group, email
    Conversation-related keys (details_status, missing_fields, follow_up_message, full_thread_summary)
    are now handled separately per conversation.
    """
    if not data.get("email"):
        raise ValueError("Email is required")

    # ✅ Normalize common "empty" values
    def _clean_str(x):
        if x is None:
            return None
        if isinstance(x, str):
            x = x.strip()
            return x if x else None
        return x

    # Clean important fields
    data = dict(data)  # copy so we don't mutate caller
    data["email"] = _clean_str(data.get("email"))
    data["full_name"] = _clean_str(data.get("full_name"))
    data["admission_number"] = _clean_str(data.get("admission_number"))
    data["course"] = _clean_str(data.get("course"))
    data["year"] = _clean_str(data.get("year"))
    data["semester"] = _clean_str(data.get("semester"))
    data["group"] = _clean_str(data.get("group"))

    admission_number = data.get("admission_number")
    student = None

    # Prefer lookup by admission number if present
    if admission_number:
        student = get_student_by_admission_number(db, admission_number)
    if not student:
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

    student_data = {k: data.get(k) for k in student_fields}

    if student:
        # ✅ Only update fields if we have a non-empty value
        # ✅ Never overwrite an existing admission_number with None/blank
        for key, value in student_data.items():
            if value is None:
                continue
            if key == "admission_number" and not value:
                continue
            setattr(student, key, value)
    else:
        # ✅ If admission_number is None, that's okay — but DO NOT set empty string
        student = Student(**{k: v for k, v in student_data.items() if v is not None})
        db.add(student)

    # --- Handle Conversation fields if thread_id provided ---
    if thread_id:
        convo_fields = {
            "details_status",
            "missing_fields",
            "follow_up_message",
            "full_thread_summary",
        }
        convo_data = {k: v for k, v in data.items() if k in convo_fields and v is not None}

        if convo_data:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.thread_id == thread_id)
                .first()
            )

            if not conversation:
                conversation = Conversation(
                    student_id=student.id if student.id else None,
                    thread_id=thread_id,
                )
                db.add(conversation)

            for key, value in convo_data.items():
                setattr(conversation, key, value)

    # ✅ Commit once at end
    db.commit()
    db.refresh(student)
    return student
