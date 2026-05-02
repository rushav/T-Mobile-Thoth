from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, JSON, Table,
)
from sqlalchemy.orm import relationship
from database import Base


sme_subjects = Table(
    "sme_subjects",
    Base.metadata,
    Column("profile_id", Integer, ForeignKey("profiles.id"), primary_key=True),
    Column("subject_id", Integer, ForeignKey("subjects.id"), primary_key=True),
)


class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # user | sme | admin
    expertise_area = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)
    review_requested_at = Column(DateTime, nullable=True)
    review_requested_by_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    review_request_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    subjects = relationship("Subject", secondary=sme_subjects, back_populates="smes")
    contributions = relationship("KnowledgeEntry", back_populates="contributor", foreign_keys="KnowledgeEntry.contributor_id")
    review_requested_by = relationship("Profile", remote_side=[id], foreign_keys=[review_requested_by_id])


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    smes = relationship("Profile", secondary=sme_subjects, back_populates="subjects")
    entries = relationship("KnowledgeEntry", back_populates="subject")


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    contributor_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    # Lifecycle: pending | pending_admin_review | approved | rejected
    status = Column(String, default="pending")
    rejection_reason = Column(Text, nullable=True)
    approved_by = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    review_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subject = relationship("Subject", back_populates="entries")
    contributor = relationship("Profile", back_populates="contributions", foreign_keys=[contributor_id])
    files = relationship("UploadedFile", back_populates="entry")


class UploadedFile(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey("knowledge_entries.id"), nullable=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    extracted_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    entry = relationship("KnowledgeEntry", back_populates="files")
    interview = relationship("Interview", back_populates="files")


class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True)
    sme_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    mode = Column(String, default="structured")  # structured | freeform
    messages = Column(JSON, default=list)
    synthesis = Column(Text, nullable=True)
    synthesis_status = Column(String, default="draft")  # draft | pending_review | approved | rejected
    entry_id = Column(Integer, ForeignKey("knowledge_entries.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sme = relationship("Profile", foreign_keys=[sme_id])
    subject = relationship("Subject")
    files = relationship("UploadedFile", back_populates="interview")


class Escalation(Base):
    __tablename__ = "escalations"
    id = Column(Integer, primary_key=True)
    user_query = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    reason = Column(Text, nullable=True)
    candidates = Column(JSON, default=list)  # [{subject, confidence}]
    status = Column(String, default="open")  # open | assigned | resolved
    assigned_to = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("Profile", foreign_keys=[user_id])
    assignee = relationship("Profile", foreign_keys=[assigned_to])


class QueryHistory(Base):
    __tablename__ = "query_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    status = Column(String, default="answered")  # answered | clarifying | escalated
    confidence = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("Profile")
    subject = relationship("Subject")
