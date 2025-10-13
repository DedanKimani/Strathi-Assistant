# backend/strathy_app/services/student_service.py
from sqlalchemy.orm import Session
from models.models import Student

def get_student_by_email(db: Session, email: str):
    return db.query(Student).filter(Student.email == email).first()

def create_or_update_student(db: Session, data: dict):
    """
    data should contain: email (required), student_name, admission_number, course, group_name, notes
    """
    if not data.get("email"):
        raise ValueError("email required")
    s = get_student_by_email(db, data["email"])
    if s:
        # update fields that are provided (do not overwrite with empty strings)
        if data.get("student_name"):
            s.student_name = data["student_name"]
        if data.get("admission_number"):
            s.admission_number = data["admission_number"]
        if data.get("course"):
            s.course = data["course"]
        if data.get("group_name"):
            s.group_name = data["group_name"]
        if data.get("notes"):
            s.notes = data["notes"]
        db.add(s)
        db.commit()
        db.refresh(s)
        return s
    else:
        s = Student(
            email=data["email"],
            student_name=data.get("student_name"),
            admission_number=data.get("admission_number"),
            course=data.get("course"),
            group_name=data.get("group_name"),
            notes=data.get("notes"),
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s
