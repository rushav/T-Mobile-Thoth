from datetime import datetime
from sqlalchemy.orm import Session
import models
import vector_store


VALID_STATUSES = {"pending", "pending_admin_review", "approved", "rejected"}


def create_entry(
    db: Session,
    subject_id: int,
    title: str,
    content: str,
    contributor_id: int | None = None,
    status: str = "pending",
) -> models.KnowledgeEntry:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
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


def submit_for_admin_review(db: Session, entry_id: int, sme_id: int | None = None) -> models.KnowledgeEntry:
    """SME has approved the synthesis. Move it to admin review queue.

    Does NOT add to ChromaDB — only admin approval does that.
    """
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise ValueError("Entry not found")
    entry.status = "pending_admin_review"
    db.commit()
    db.refresh(entry)
    return entry


def admin_approve_entry(db: Session, entry_id: int, approver_id: int | None = None) -> models.KnowledgeEntry:
    """Final approval by admin. Adds the entry to ChromaDB."""
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


# Back-compat alias for any callers that haven't been migrated.
approve_entry = admin_approve_entry


def reject_entry(db: Session, entry_id: int, reason: str | None = None) -> models.KnowledgeEntry:
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise ValueError("Entry not found")
    entry.status = "rejected"
    if reason is not None:
        entry.rejection_reason = reason
    db.commit()
    db.refresh(entry)
    vector_store.remove_entry(entry.subject_id, entry.id)
    return entry


def update_entry_content(db: Session, entry_id: int, title: str | None, content: str) -> models.KnowledgeEntry:
    """Replace an entry's content (used after revision). Does NOT change status."""
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise ValueError("Entry not found")
    if title is not None:
        entry.title = title
    entry.content = content
    db.commit()
    db.refresh(entry)
    return entry
