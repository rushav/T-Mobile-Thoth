from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import models
from agents import interviewer
from services import knowledge as knowledge_svc

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


class StartPayload(BaseModel):
    sme_id: int
    subject_id: int


class StartResponse(BaseModel):
    interview_id: int
    opening_message: str


@router.post("/start", response_model=StartResponse)
def start_interview(payload: StartPayload, db: Session = Depends(get_db)):
    sme = db.query(models.Profile).filter(models.Profile.id == payload.sme_id).first()
    subject = db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first()
    if not sme or sme.role != "sme":
        raise HTTPException(status_code=404, detail="SME not found")
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    opening = interviewer.next_message(sme.name, subject.name, messages=[])

    interview = models.Interview(
        sme_id=sme.id,
        subject_id=subject.id,
        messages=[{"role": "assistant", "content": opening, "ts": datetime.utcnow().isoformat()}],
        synthesis_status="draft",
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return StartResponse(interview_id=interview.id, opening_message=opening)


class MessagePayload(BaseModel):
    content: str


class MessageResponse(BaseModel):
    reply: str
    messages: list[dict]


@router.post("/{interview_id}/message", response_model=MessageResponse)
def send_message(interview_id: int, payload: MessagePayload, db: Session = Depends(get_db)):
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    msgs = list(interview.messages or [])
    msgs.append({"role": "user", "content": payload.content, "ts": datetime.utcnow().isoformat()})

    # Build history for LLM (drop timestamps)
    history = [{"role": m["role"], "content": m["content"]} for m in msgs]
    reply = interviewer.next_message(interview.sme.name, interview.subject.name, messages=history)

    msgs.append({"role": "assistant", "content": reply, "ts": datetime.utcnow().isoformat()})
    interview.messages = msgs
    db.commit()
    db.refresh(interview)
    return MessageResponse(reply=reply, messages=msgs)


class SynthesizeResponse(BaseModel):
    synthesis: str
    entry_id: int


@router.post("/{interview_id}/synthesize", response_model=SynthesizeResponse)
def synthesize(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    transcript = interviewer.transcript_from_messages(interview.messages or [])
    uploaded_parts = [f.extracted_text or "" for f in interview.files if f.extracted_text]
    uploaded_text = "\n\n".join(uploaded_parts)

    synthesis = interviewer.synthesize(
        sme_name=interview.sme.name,
        subject_name=interview.subject.name,
        transcript=transcript,
        uploaded_text=uploaded_text,
    )

    interview.synthesis = synthesis
    interview.synthesis_status = "pending_review"

    # Create a pending knowledge entry tied to this interview
    first_line = next((l for l in synthesis.splitlines() if l.strip()), f"Interview {interview.id}")
    title = first_line.strip("# *").strip()[:120] or f"Interview {interview.id}"
    entry = models.KnowledgeEntry(
        subject_id=interview.subject_id,
        contributor_id=interview.sme_id,
        title=title,
        content=synthesis,
        status="pending",
    )
    db.add(entry)
    db.flush()
    interview.entry_id = entry.id
    db.commit()
    db.refresh(entry)
    return SynthesizeResponse(synthesis=synthesis, entry_id=entry.id)


class ReviewPayload(BaseModel):
    action: str  # approve | reject | request_changes
    feedback: str | None = None


@router.post("/{interview_id}/review")
def review(interview_id: int, payload: ReviewPayload, db: Session = Depends(get_db)):
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    if not interview.entry_id:
        raise HTTPException(status_code=400, detail="No synthesis yet; call /synthesize first")

    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == interview.entry_id).first()
    if payload.action == "approve":
        knowledge_svc.approve_entry(db, entry.id, approver_id=interview.sme_id)
        interview.synthesis_status = "approved"
        db.commit()
        return {"status": "approved", "entry_id": entry.id}

    if payload.action == "reject":
        knowledge_svc.reject_entry(db, entry.id)
        interview.synthesis_status = "rejected"
        db.commit()
        return {"status": "rejected", "entry_id": entry.id}

    if payload.action == "request_changes":
        interview.synthesis_status = "draft"
        # Append feedback as a new SME turn so the next synthesize considers it
        msgs = list(interview.messages or [])
        if payload.feedback:
            msgs.append({
                "role": "user",
                "content": f"[Revision feedback] {payload.feedback}",
                "ts": datetime.utcnow().isoformat(),
            })
            interview.messages = msgs
        db.commit()
        return {"status": "draft", "entry_id": entry.id}

    raise HTTPException(status_code=400, detail="action must be approve|reject|request_changes")


class InterviewOut(BaseModel):
    id: int
    sme_id: int
    subject_id: int
    subject_name: str
    messages: list[dict]
    synthesis: str | None
    synthesis_status: str
    entry_id: int | None


@router.get("/{interview_id}", response_model=InterviewOut)
def get_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return InterviewOut(
        id=interview.id,
        sme_id=interview.sme_id,
        subject_id=interview.subject_id,
        subject_name=interview.subject.name,
        messages=interview.messages or [],
        synthesis=interview.synthesis,
        synthesis_status=interview.synthesis_status,
        entry_id=interview.entry_id,
    )
