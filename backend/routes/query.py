import time
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import models
from session import get_current_profile
from agents import thoth
from config import UPLOADS_DIR
from services import file_parser

router = APIRouter(prefix="/api/query", tags=["query"])


MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
TEXT_EXT = {".pdf", ".docx", ".txt", ".md"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_EXT = TEXT_EXT | IMAGE_EXT
CONTEXT_CHAR_LIMIT = 2000


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


def _save_upload(file: UploadFile, content: bytes) -> Path:
    """Save the uploaded file with a timestamped, unique name."""
    safe_orig = Path(file.filename or "upload").name
    stamp = time.strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    dest = Path(UPLOADS_DIR) / f"{stamp}_{short_id}_{safe_orig}"
    dest.write_bytes(content)
    return dest


def _build_extra_context(filename: str, ext: str, dest_path: Path) -> tuple[str, str]:
    """Return (extra_context_for_llm, extracted_text_preview_for_response)."""
    if ext in IMAGE_EXT:
        note = f"User attached an image: {filename}"
        return note, ""

    text = file_parser.extract_text(str(dest_path), filename) or ""
    truncated = text[:CONTEXT_CHAR_LIMIT]
    extra = (
        f"The user also attached a file ({filename}) with this content:\n{truncated}"
        if truncated.strip()
        else f"User attached a file ({filename}) but no text could be extracted."
    )
    return extra, text


@router.post("/with-file")
async def query_with_file(
    question: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    profile: models.Profile | None = Depends(get_current_profile),
):
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type {ext}. Allowed: {sorted(ALLOWED_EXT)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large ({len(content)} bytes). Max is {MAX_FILE_BYTES} bytes (5 MB).",
        )
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    dest = _save_upload(file, content)

    extra_context, full_text = _build_extra_context(file.filename or dest.name, ext, dest)

    rec = models.UploadedFile(
        filename=file.filename or dest.name,
        filepath=str(dest),
        file_type=ext.lstrip("."),
        extracted_text=full_text or None,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    user_id = profile.id if profile else None
    result = thoth.handle_query(db, question, user_id, extra_context=extra_context)
    result["attachment"] = {
        "id": rec.id,
        "filename": rec.filename,
        "file_type": rec.file_type,
        "is_image": ext in IMAGE_EXT,
        "extracted_chars": len(full_text or ""),
    }
    return result


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
