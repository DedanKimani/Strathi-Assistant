# backend/strathy_app/services/student_service.py

from sqlalchemy.orm import Session
from backend.strathy_app.models.models import Student
import json

def get_student_by_email(db: Session, email: str):
    return db.query(Student).filter(Student.email == email).first()


def create_or_update_student(db: Session, data: dict):
    """
    Create or update a student record.
    Expected keys: full_name, admission_number, course, year, semester, group, email
    Also supports: details_status, missing_fields (list or json), follow_up_message, full_thread_summary
    """
    if not data.get("email"):
        raise ValueError("Email is required")

    student = get_student_by_email(db, data["email"])

    # Normalize missing_fields if provided as list -> dict/jsonb
    if "missing_fields" in data and data["missing_fields"] is not None:
        mf = data["missing_fields"]
        # If it's a string (JSON), try to load
        if isinstance(mf, str):
            try:
                data["missing_fields"] = json.loads(mf)
            except Exception:
                # fallback: keep as string inside array
                data["missing_fields"] = [mf]
        # if it's list, leave it
        elif not isinstance(mf, (list, dict)):
            # convert scalar to list
            data["missing_fields"] = [mf]

    if student:
        # Update only non-empty fields; allow explicit empty string to clear some fields if needed
        for key, value in data.items():
            if hasattr(student, key) and value is not None:
                setattr(student, key, value)
    else:
        # Filter fields to model init
        init_data = {k: v for k, v in data.items() if hasattr(Student, k)}
        student = Student(**init_data)
        db.add(student)

    db.commit()
    db.refresh(student)
    return student
