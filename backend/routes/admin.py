from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import models
from services import knowledge as knowledge_svc

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/pending")
def pending(db: Session = Depends(get_db)):
    rows = (
        db.query(models.KnowledgeEntry)
        .filter(models.KnowledgeEntry.status == "pending")
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


class ApprovePayload(BaseModel):
    approver_id: int | None = None


@router.post("/approve/{entry_id}")
def approve(entry_id: int, payload: ApprovePayload | None = None, db: Session = Depends(get_db)):
    approver_id = payload.approver_id if payload else None
    try:
        entry = knowledge_svc.approve_entry(db, entry_id, approver_id=approver_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": entry.status, "entry_id": entry.id}


@router.post("/reject/{entry_id}")
def reject(entry_id: int, db: Session = Depends(get_db)):
    try:
        entry = knowledge_svc.reject_entry(db, entry_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": entry.status, "entry_id": entry.id}


@router.get("/escalations")
def escalations(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Escalation)
        .filter(models.Escalation.status != "resolved")
        .order_by(models.Escalation.created_at.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "user_query": e.user_query,
            "user_id": e.user_id,
            "user_name": e.user.name if e.user else None,
            "reason": e.reason,
            "status": e.status,
            "assigned_to": e.assigned_to,
            "resolution": e.resolution,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in rows
    ]


class ResolvePayload(BaseModel):
    resolution: str
    admin_id: int | None = None


@router.post("/escalations/{escalation_id}/resolve")
def resolve_escalation(escalation_id: int, payload: ResolvePayload, db: Session = Depends(get_db)):
    esc = db.query(models.Escalation).filter(models.Escalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    esc.resolution = payload.resolution
    esc.status = "resolved"
    esc.assigned_to = payload.admin_id
    db.commit()
    db.refresh(esc)
    return {"id": esc.id, "status": esc.status}


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
                {"id": p.id, "name": p.name, "expertise_area": p.expertise_area}
                for p in s.smes
            ],
        })
    # Also list SMEs without any subject mapping
    unassigned = [
        p for p in db.query(models.Profile).filter(models.Profile.role == "sme").all()
        if not p.subjects
    ]
    if unassigned:
        out.append({
            "subject_id": None,
            "subject_name": "(unassigned)",
            "description": None,
            "smes": [{"id": p.id, "name": p.name, "expertise_area": p.expertise_area} for p in unassigned],
        })
    return out
