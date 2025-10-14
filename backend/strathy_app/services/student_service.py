# backend/strathy_app/services/student_service.py

from sqlalchemy.orm import Session
from backend.strathy_app.models.models import Student

def get_student_by_email(db: Session, email: str):
    return db.query(Student).filter(Student.email == email).first()


def create_or_update_student(db: Session, data: dict):
    """
    Create or update a student record.
    Expected keys: full_name, admission_number, course, year, semester, group, email
    """
    if not data.get("email"):
        raise ValueError("Email is required")

    student = get_student_by_email(db, data["email"])

    if student:
        # Update only non-empty fields
        for key, value in data.items():
            if hasattr(student, key) and value:
                setattr(student, key, value)
    else:
        student = Student(**data)
        db.add(student)

    db.commit()
    db.refresh(student)
    return student
