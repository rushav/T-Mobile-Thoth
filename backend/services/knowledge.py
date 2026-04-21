from datetime import datetime
from sqlalchemy.orm import Session
import models
import vector_store


def create_entry(
    db: Session,
    subject_id: int,
    title: str,
    content: str,
    contributor_id: int | None = None,
    status: str = "pending",
) -> models.KnowledgeEntry:
    entry = models.KnowledgeEntry(
        subject_id=subject_id,
        title=title,
        content=content,
        contributor_id=contributor_id,
        status=status,
    )
    if status == "approved":
        entry.approved_at = datetime.utcnow()
    db.add(entry)
    db.commit()
    db.refresh(entry)
    if status == "approved":
        vector_store.add_entry(subject_id, entry.id, title, content)
    return entry


def approve_entry(db: Session, entry_id: int, approver_id: int | None = None) -> models.KnowledgeEntry:
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise ValueError("Entry not found")
    entry.status = "approved"
    entry.approved_by = approver_id
    entry.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    vector_store.add_entry(entry.subject_id, entry.id, entry.title, entry.content)
    return entry


def reject_entry(db: Session, entry_id: int) -> models.KnowledgeEntry:
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise ValueError("Entry not found")
    entry.status = "rejected"
    db.commit()
    db.refresh(entry)
    vector_store.remove_entry(entry.subject_id, entry.id)
    return entry
