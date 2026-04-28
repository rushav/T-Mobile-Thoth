from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import models
from services import knowledge as knowledge_svc

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/pending")
def pending_for_sme(sme_id: int, db: Session = Depends(get_db)):
    """Pending entries where this SME is listed as an expert for the subject."""
    sme = db.query(models.Profile).filter(
        models.Profile.id == sme_id, models.Profile.role == "sme"
    ).first()
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")
    subject_ids = [s.id for s in sme.subjects]
    if not subject_ids:
        return []
    rows = (
        db.query(models.KnowledgeEntry)
        .filter(
            models.KnowledgeEntry.status == "pending",
            models.KnowledgeEntry.subject_id.in_(subject_ids),
        )
        .order_by(models.KnowledgeEntry.created_at.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "title": e.title,
            "content": e.content,
            "subject_id": e.subject_id,
            "subject_name": e.subject.name if e.subject else None,
            "contributor_id": e.contributor_id,
            "contributor_name": e.contributor.name if e.contributor else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in rows
    ]


class ReviewAction(BaseModel):
    action: str  # approve | reject
    reviewer_id: int | None = None
    feedback: str | None = None


@router.post("/{entry_id}")
def review_entry(entry_id: int, payload: ReviewAction, db: Session = Depends(get_db)):
    """SME-level review: approve forwards to admin queue, reject closes the entry."""
    if payload.action == "approve":
        entry = knowledge_svc.submit_for_admin_review(db, entry_id, sme_id=payload.reviewer_id)
        return {"status": entry.status, "entry_id": entry.id}
    if payload.action == "reject":
        entry = knowledge_svc.reject_entry(db, entry_id, reason=payload.feedback)
        return {"status": entry.status, "entry_id": entry.id}
    raise HTTPException(status_code=400, detail="action must be approve or reject")
