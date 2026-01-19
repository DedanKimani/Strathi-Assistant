from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from dotenv import load_dotenv
import os

# ====== Setup ======
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set in .env")

engine = create_engine(DATABASE_URL)
Base = declarative_base()


# =========================
# 🧑‍🎓 STUDENT MODEL
# =========================
class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    admission_number = Column(String, unique=True, index=True)
    course = Column(String, nullable=True)
    year = Column(String, nullable=True)
    semester = Column(String, nullable=True)
    group = Column(String, nullable=True)
    email = Column(String, index=True)

    # 🕓 Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversations = relationship("Conversation", back_populates="student")


# =========================
# 💬 CONVERSATION MODEL
# =========================
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, unique=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    subject = Column(String)
    message_body = Column(Text, default="")  # <-- Store the raw email text
    last_updated = Column(DateTime, default=datetime.utcnow)

    # 🆕 Per-thread extracted fields (moved from Student)
    full_thread_summary = Column(Text, nullable=True)
    details_status = Column(String(20), nullable=False, default="empty")  # 'complete' | 'partial' | 'empty'
    missing_fields = Column(JSONB, nullable=False, default=list)
    follow_up_message = Column(Text, nullable=True)

    # Relationships
    student = relationship("Student", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


# =========================
# ✉️ MESSAGE MODEL
# =========================
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    sender_email = Column(String)
    sender_name = Column(String)
    subject = Column(String)
    body = Column(Text)
    role = Column(String)  # 'student' or 'ADAM'
    sent_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


# =========================
# ⚙️ DATABASE INIT
# =========================
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
