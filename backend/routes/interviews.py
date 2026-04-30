from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from database import get_db
import models
from agents import interviewer
from services import knowledge as knowledge_svc

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


VALID_MODES = {"structured", "freeform"}


def _serialize_file(f) -> dict:
    return {
        "id": f.id,
        "filename": f.filename,
        "file_type": f.file_type,
        "extracted_chars": len(f.extracted_text or ""),
    }


def _serialize_interview(interview: models.Interview) -> dict:
    return {
        "id": interview.id,
        "sme_id": interview.sme_id,
        "subject_id": interview.subject_id,
        "subject_name": interview.subject.name if interview.subject else None,
        "created_at": interview.created_at.isoformat() if interview.created_at else None,
        "mode": interview.mode,
        "messages": interview.messages or [],
        "synthesis": interview.synthesis,
        "synthesis_status": interview.synthesis_status,
        "entry_id": interview.entry_id,
        "files": [_serialize_file(f) for f in (interview.files or [])],
    }


class StartPayload(BaseModel):
    sme_id: int
    subject_id: int
    mode: str | None = "structured"


class StartResponse(BaseModel):
    interview_id: int
    opening_message: str
    mode: str


@router.post("/start", response_model=StartResponse)
def start_interview(payload: StartPayload, db: Session = Depends(get_db)):
    sme = db.query(models.Profile).filter(models.Profile.id == payload.sme_id).first()
    subject = db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first()
    if not sme or sme.role != "sme":
        raise HTTPException(status_code=404, detail="SME not found")
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # SME may only run interviews on their own subjects.
    sme_subject_ids = {s.id for s in sme.subjects}
    if subject.id not in sme_subject_ids:
        raise HTTPException(
            status_code=403,
            detail="This subject is not assigned to you. Pick one of your own subjects.",
        )

    mode = payload.mode if payload.mode in VALID_MODES else "structured"
    opening = interviewer.next_message(sme.name, subject.name, messages=[], mode=mode)

    interview = models.Interview(
        sme_id=sme.id,
        subject_id=subject.id,
        mode=mode,
        messages=[{"role": "assistant", "content": opening, "ts": datetime.utcnow().isoformat()}],
        synthesis_status="draft",
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return StartResponse(interview_id=interview.id, opening_message=opening, mode=mode)


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

    history = [{"role": m["role"], "content": m["content"]} for m in msgs]
    reply = interviewer.next_message(
        interview.sme.name,
        interview.subject.name,
        messages=history,
        mode=interview.mode or "structured",
    )

    msgs.append({"role": "assistant", "content": reply, "ts": datetime.utcnow().isoformat()})
    interview.messages = msgs
    db.commit()
    db.refresh(interview)
    return MessageResponse(reply=reply, messages=msgs)


def _title_from_synthesis(synthesis: str, fallback: str) -> str:
    first_line = next((l for l in (synthesis or "").splitlines() if l.strip()), fallback)
    return first_line.strip("# *").strip()[:120] or fallback


@router.post("/{interview_id}/synthesize")
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
        mode=interview.mode or "structured",
    )

    interview.synthesis = synthesis
    interview.synthesis_status = "pending_review"

    title = _title_from_synthesis(synthesis, f"Interview {interview.id}")

    if interview.entry_id:
        # Revising an existing draft entry — replace its content rather than create a new one.
        knowledge_svc.update_entry_content(db, interview.entry_id, title=title, content=synthesis)
        entry_id = interview.entry_id
    else:
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
        entry_id = entry.id

    db.commit()
    db.refresh(interview)
    return {"synthesis": synthesis, "entry_id": entry_id, "interview": _serialize_interview(interview)}


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
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry missing")

    if payload.action == "approve":
        # SME-level approval moves the entry to the admin queue. NOT yet in the KB.
        knowledge_svc.submit_for_admin_review(db, entry.id, sme_id=interview.sme_id)
        interview.synthesis_status = "approved"  # SME side is done.
        db.commit()
        return {
            "status": "pending_admin_review",
            "entry_id": entry.id,
            "interview": _serialize_interview(interview),
        }

    if payload.action == "reject":
        knowledge_svc.reject_entry(db, entry.id, reason=payload.feedback)
        interview.synthesis_status = "rejected"
        db.commit()
        return {
            "status": "rejected",
            "entry_id": entry.id,
            "interview": _serialize_interview(interview),
        }

    if payload.action == "request_changes":
        # Send transcript + previous synthesis + feedback back to Claude for revision.
        transcript = interviewer.transcript_from_messages(interview.messages or [])
        uploaded_parts = [f.extracted_text or "" for f in interview.files if f.extracted_text]
        uploaded_text = "\n\n".join(uploaded_parts)

        revised = interviewer.revise(
            sme_name=interview.sme.name,
            subject_name=interview.subject.name,
            transcript=transcript,
            uploaded_text=uploaded_text,
            previous_synthesis=interview.synthesis or "",
            feedback=payload.feedback or "",
        )

        # Update both the interview synthesis and the linked entry. Status stays pending_review
        # so the SME reviews the revision.
        title = _title_from_synthesis(revised, entry.title)
        knowledge_svc.update_entry_content(db, entry.id, title=title, content=revised)
        interview.synthesis = revised
        interview.synthesis_status = "pending_review"
        db.commit()
        db.refresh(interview)
        return {
            "status": "pending_review",
            "entry_id": entry.id,
            "synthesis": revised,
            "interview": _serialize_interview(interview),
        }

    raise HTTPException(status_code=400, detail="action must be approve|reject|request_changes")


@router.get("/{interview_id}")
def get_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return _serialize_interview(interview)


@router.get("")
def list_interviews(sme_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Interview).options(joinedload(models.Interview.files))
    if sme_id is not None:
        q = q.filter(models.Interview.sme_id == sme_id)
    rows = q.order_by(models.Interview.created_at.desc()).all()
    return [_serialize_interview(i) for i in rows]
