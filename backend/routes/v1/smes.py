"""V1 SME profile, interview, material, and synthesis endpoints."""
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import models
from agents import interviewer_v1
from services.token_tracker import TokenTracker
from services import file_parser
from config import UPLOADS_DIR

router = APIRouter(prefix="/api/v1/smes", tags=["v1-smes"])

ACCEPTED_MIME = {"application/pdf", "text/plain", "text/markdown"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _iso(dt) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _sme_dict(sme: models.V1SMEProfile) -> dict:
    return {
        "sme_id": sme.sme_id,
        "name": sme.name,
        "specialization": sme.specialization,
        "sub_areas": sme.sub_areas or [],
        "contact_email": sme.contact_email,
        "created_at": _iso(sme.created_at),
    }


def _interview_dict(iv: models.V1Interview) -> dict:
    return {
        "interview_id": iv.interview_id,
        "sme_id": iv.sme_id,
        "topic": iv.topic,
        "status": iv.status,
        "created_at": _iso(iv.created_at),
    }


def _entry_dict(e: models.V1KnowledgeEntry) -> dict:
    return {
        "entry_id": e.entry_id,
        "sme_id": e.sme_id,
        "topic": e.topic,
        "status": e.status,
        "content": e.content,
        "sources": e.sources or {},
        "created_at": _iso(e.created_at),
        "updated_at": _iso(e.updated_at),
    }


# ── SME CRUD ──────────────────────────────────────────────────────────────────

class SMECreate(BaseModel):
    name: str
    specialization: str
    sub_areas: list[str]
    contact_email: str


@router.post("", status_code=201)
def create_sme(payload: SMECreate, db: Session = Depends(get_db)):
    sme = models.V1SMEProfile(
        sme_id=_new_id("sme"),
        name=payload.name,
        specialization=payload.specialization,
        sub_areas=payload.sub_areas,
        contact_email=payload.contact_email,
    )
    db.add(sme)
    db.commit()
    db.refresh(sme)
    return _sme_dict(sme)


@router.get("")
def list_smes(db: Session = Depends(get_db)):
    smes = db.query(models.V1SMEProfile).order_by(models.V1SMEProfile.created_at).all()
    return {"smes": [_sme_dict(s) for s in smes]}


@router.get("/{sme_id}")
def get_sme(sme_id: str, db: Session = Depends(get_db)):
    sme = db.query(models.V1SMEProfile).filter(models.V1SMEProfile.sme_id == sme_id).first()
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")
    return _sme_dict(sme)


# ── Interviews ────────────────────────────────────────────────────────────────

class InterviewStart(BaseModel):
    topic: str


@router.post("/{sme_id}/interviews", status_code=201)
def start_interview(sme_id: str, payload: InterviewStart, db: Session = Depends(get_db)):
    sme = db.query(models.V1SMEProfile).filter(models.V1SMEProfile.sme_id == sme_id).first()
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")
    iv = models.V1Interview(
        interview_id=_new_id("int"),
        sme_id=sme_id,
        topic=payload.topic,
        status="in_progress",
        turns=[],
    )
    db.add(iv)
    db.commit()
    db.refresh(iv)
    return _interview_dict(iv)


@router.get("/{sme_id}/interviews")
def list_interviews(sme_id: str, db: Session = Depends(get_db)):
    sme = db.query(models.V1SMEProfile).filter(models.V1SMEProfile.sme_id == sme_id).first()
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")
    ivs = (
        db.query(models.V1Interview)
        .filter(models.V1Interview.sme_id == sme_id)
        .order_by(models.V1Interview.created_at)
        .all()
    )
    return {"interviews": [_interview_dict(iv) for iv in ivs]}


# ── Materials ─────────────────────────────────────────────────────────────────

@router.post("/{sme_id}/materials", status_code=201)
async def upload_material(
    sme_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(default=""),
    db: Session = Depends(get_db),
):
    sme = db.query(models.V1SMEProfile).filter(models.V1SMEProfile.sme_id == sme_id).first()
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")

    content_type = file.content_type or ""
    if content_type not in ACCEPTED_MIME:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Accepted: {sorted(ACCEPTED_MIME)}",
        )

    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit")

    dest_name = f"{uuid.uuid4().hex}_{Path(file.filename or 'upload').name}"
    dest = Path(UPLOADS_DIR) / dest_name
    dest.write_bytes(raw)

    try:
        extracted = file_parser.extract_text(str(dest), file.filename or "")
        status = "processed"
    except Exception:
        extracted = None
        status = "failed"

    mat = models.V1Material(
        material_id=_new_id("mat"),
        sme_id=sme_id,
        title=title,
        file_type=content_type,
        description=description or None,
        extracted_text=extracted,
        status=status,
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return {
        "material_id": mat.material_id,
        "sme_id": mat.sme_id,
        "title": mat.title,
        "file_type": mat.file_type,
        "status": mat.status,
        "created_at": _iso(mat.created_at),
    }


@router.get("/{sme_id}/materials")
def list_materials(sme_id: str, db: Session = Depends(get_db)):
    sme = db.query(models.V1SMEProfile).filter(models.V1SMEProfile.sme_id == sme_id).first()
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")
    mats = (
        db.query(models.V1Material)
        .filter(models.V1Material.sme_id == sme_id)
        .order_by(models.V1Material.created_at)
        .all()
    )
    return {
        "materials": [
            {
                "material_id": m.material_id,
                "title": m.title,
                "file_type": m.file_type,
                "status": m.status,
                "created_at": _iso(m.created_at),
            }
            for m in mats
        ]
    }


# ── Synthesize ────────────────────────────────────────────────────────────────

class SynthesizeRequest(BaseModel):
    interview_ids: list[str]
    material_ids: list[str]
    topic: str


@router.post("/{sme_id}/knowledge/synthesize", status_code=201)
def synthesize_knowledge(sme_id: str, payload: SynthesizeRequest, db: Session = Depends(get_db)):
    sme = db.query(models.V1SMEProfile).filter(models.V1SMEProfile.sme_id == sme_id).first()
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")

    all_turns: list[dict] = []
    for iid in payload.interview_ids:
        iv = db.query(models.V1Interview).filter(models.V1Interview.interview_id == iid).first()
        if iv:
            all_turns.extend(iv.turns or [])

    material_texts: list[str] = []
    for mid in payload.material_ids:
        mat = db.query(models.V1Material).filter(models.V1Material.material_id == mid).first()
        if mat and mat.extracted_text:
            material_texts.append(f"[{mat.title}]\n{mat.extracted_text}")

    tracker = TokenTracker()
    content, tracker = interviewer_v1.synthesize(
        topic=payload.topic,
        turns=all_turns,
        material_texts=material_texts,
        tracker=tracker,
    )

    entry = models.V1KnowledgeEntry(
        entry_id=_new_id("ke"),
        sme_id=sme_id,
        topic=payload.topic,
        status="draft",
        content=content,
        sources={"interviews": payload.interview_ids, "materials": payload.material_ids},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    result = _entry_dict(entry)
    result["usage"] = tracker.to_dict()
    return result
