from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import models
from session import get_current_profile
from agents import thoth

router = APIRouter(prefix="/api/query", tags=["query"])


class QueryPayload(BaseModel):
    question: str


@router.post("")
def query(
    payload: QueryPayload,
    db: Session = Depends(get_db),
    profile: models.Profile | None = Depends(get_current_profile),
):
    user_id = profile.id if profile else None
    return thoth.handle_query(db, payload.question, user_id)


@router.get("/history")
def history(
    db: Session = Depends(get_db),
    profile: models.Profile | None = Depends(get_current_profile),
):
    if not profile:
        return []
    rows = (
        db.query(models.QueryHistory)
        .filter(models.QueryHistory.user_id == profile.id)
        .order_by(models.QueryHistory.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "status": r.status,
            "subject_id": r.subject_id,
            "subject_name": r.subject.name if r.subject else None,
            "confidence": r.confidence,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
