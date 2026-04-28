from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import models
from services import knowledge as knowledge_svc

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _serialize_entry(e: models.KnowledgeEntry) -> dict:
    return {
        "id": e.id,
        "title": e.title,
        "content": e.content,
        "status": e.status,
        "subject_id": e.subject_id,
        "subject_name": e.subject.name if e.subject else None,
        "contributor_id": e.contributor_id,
        "contributor_name": e.contributor.name if e.contributor else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/pending")
def pending(db: Session = Depends(get_db)):
    """Entries waiting for final admin approval (after SME approval)."""
    rows = (
        db.query(models.KnowledgeEntry)
        .filter(models.KnowledgeEntry.status == "pending_admin_review")
        .order_by(models.KnowledgeEntry.created_at.desc())
        .all()
    )
    return [_serialize_entry(e) for e in rows]


class ApprovePayload(BaseModel):
    approver_id: int | None = None


@router.post("/approve/{entry_id}")
def approve(entry_id: int, payload: ApprovePayload | None = None, db: Session = Depends(get_db)):
    approver_id = payload.approver_id if payload else None
    try:
        entry = knowledge_svc.admin_approve_entry(db, entry_id, approver_id=approver_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": entry.status, "entry_id": entry.id}


class RejectPayload(BaseModel):
    reason: str | None = None


@router.post("/reject/{entry_id}")
def reject(entry_id: int, payload: RejectPayload | None = None, db: Session = Depends(get_db)):
    reason = payload.reason if payload else None
    try:
        entry = knowledge_svc.reject_entry(db, entry_id, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": entry.status, "entry_id": entry.id}


def _serialize_escalation(e: models.Escalation) -> dict:
    return {
        "id": e.id,
        "user_query": e.user_query,
        "user_id": e.user_id,
        "user_name": e.user.name if e.user else None,
        "reason": e.reason,
        "candidates": e.candidates or [],
        "status": e.status,
        "assigned_to": e.assigned_to,
        "assigned_to_name": e.assignee.name if e.assignee else None,
        "resolution": e.resolution,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
    }


@router.get("/escalations")
def escalations(status: str | None = None, db: Session = Depends(get_db)):
    """List escalations. By default shows only OPEN ones (active inbox).

    Use ?status=resolved to see the archive, or ?status=all for everything.
    """
    q = db.query(models.Escalation)
    if status is None or status == "open":
        q = q.filter(models.Escalation.status != "resolved")
    elif status == "resolved":
        q = q.filter(models.Escalation.status == "resolved")
    elif status == "all":
        pass
    else:
        q = q.filter(models.Escalation.status == status)
    rows = q.order_by(models.Escalation.created_at.desc()).all()
    return [_serialize_escalation(e) for e in rows]


@router.get("/escalations/{escalation_id}")
def get_escalation(escalation_id: int, db: Session = Depends(get_db)):
    esc = db.query(models.Escalation).filter(models.Escalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return _serialize_escalation(esc)


class ResolvePayload(BaseModel):
    resolution: str
    admin_id: int | None = None


@router.post("/escalations/{escalation_id}/resolve")
def resolve_escalation(escalation_id: int, payload: ResolvePayload, db: Session = Depends(get_db)):
    esc = db.query(models.Escalation).filter(models.Escalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if not payload.resolution.strip():
        raise HTTPException(status_code=400, detail="Resolution cannot be empty")
    esc.resolution = payload.resolution
    esc.status = "resolved"
    esc.assigned_to = payload.admin_id
    esc.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(esc)
    return _serialize_escalation(esc)


@router.get("/directory")
def directory(db: Session = Depends(get_db)):
    subjects = db.query(models.Subject).order_by(models.Subject.name).all()
    out = []
    for s in subjects:
        out.append({
            "subject_id": s.id,
            "subject_name": s.name,
            "description": s.description,
            "smes": [
                {
                    "id": p.id,
                    "name": p.name,
                    "expertise_area": p.expertise_area,
                    "contact_info": p.contact_info,
                    "review_requested_at": p.review_requested_at.isoformat() if p.review_requested_at else None,
                }
                for p in s.smes
            ],
        })
    unassigned = [
        p for p in db.query(models.Profile).filter(models.Profile.role == "sme").all()
        if not p.subjects
    ]
    if unassigned:
        out.append({
            "subject_id": None,
            "subject_name": "(unassigned)",
            "description": None,
            "smes": [
                {
                    "id": p.id,
                    "name": p.name,
                    "expertise_area": p.expertise_area,
                    "contact_info": p.contact_info,
                    "review_requested_at": p.review_requested_at.isoformat() if p.review_requested_at else None,
                }
                for p in unassigned
            ],
        })
    return out


class ReviewRequestPayload(BaseModel):
    sme_id: int
    admin_id: int | None = None
    message: str | None = None


@router.post("/request-review")
def request_review(payload: ReviewRequestPayload, db: Session = Depends(get_db)):
    """Admin asks an SME to re-check their knowledge entries for accuracy."""
    sme = db.query(models.Profile).filter(
        models.Profile.id == payload.sme_id, models.Profile.role == "sme"
    ).first()
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")
    sme.review_requested_at = datetime.utcnow()
    sme.review_requested_by_id = payload.admin_id
    sme.review_request_message = (
        payload.message
        or "Admin has requested you review your knowledge entries for accuracy."
    )
    db.commit()
    db.refresh(sme)
    return {
        "sme_id": sme.id,
        "review_requested_at": sme.review_requested_at.isoformat(),
        "message": sme.review_request_message,
    }
