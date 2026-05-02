"""V1 interview turn and transcript endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import models
from agents import interviewer_v1
from services.token_tracker import TokenTracker

router = APIRouter(prefix="/api/v1/interviews", tags=["v1-interviews"])


class TurnRequest(BaseModel):
    sme_response: str


@router.post("/{interview_id}/turns")
def add_turn(interview_id: str, payload: TurnRequest, db: Session = Depends(get_db)):
    iv = db.query(models.V1Interview).filter(models.V1Interview.interview_id == interview_id).first()
    if not iv:
        raise HTTPException(status_code=404, detail="Interview not found")

    turns = list(iv.turns or [])
    turn_number = len(turns) + 1
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    pending_turn = {
        "turn_number": turn_number,
        "sme_response": payload.sme_response,
        "agent_follow_up": None,
        "timestamp": timestamp,
    }
    turns.append(pending_turn)

    tracker = TokenTracker()
    follow_up, tracker = interviewer_v1.generate_follow_up(
        topic=iv.topic,
        turns=turns,
        tracker=tracker,
    )

    turns[-1]["agent_follow_up"] = follow_up
    iv.turns = turns
    db.commit()

    return {
        "turn_number": turn_number,
        "sme_response": payload.sme_response,
        "agent_follow_up": follow_up,
        "timestamp": timestamp,
        "usage": tracker.to_dict(),
    }


@router.get("/{interview_id}")
def get_interview(interview_id: str, db: Session = Depends(get_db)):
    iv = db.query(models.V1Interview).filter(models.V1Interview.interview_id == interview_id).first()
    if not iv:
        raise HTTPException(status_code=404, detail="Interview not found")
    return {
        "interview_id": iv.interview_id,
        "sme_id": iv.sme_id,
        "topic": iv.topic,
        "status": iv.status,
        "turns": iv.turns or [],
        "created_at": iv.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if iv.created_at else None,
    }
