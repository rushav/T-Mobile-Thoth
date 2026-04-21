import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models
from config import UPLOADS_DIR
from services import file_parser

router = APIRouter(prefix="/api/files", tags=["files"])


ALLOWED_EXT = {".pdf", ".docx", ".txt", ".md"}


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    interview_id: int | None = Form(default=None),
    entry_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported file type {ext}. Allowed: {sorted(ALLOWED_EXT)}")

    safe_name = f"{uuid.uuid4().hex}_{Path(file.filename).name}"
    dest = Path(UPLOADS_DIR) / safe_name
    content = await file.read()
    dest.write_bytes(content)

    text = file_parser.extract_text(str(dest), file.filename)

    rec = models.UploadedFile(
        filename=file.filename,
        filepath=str(dest),
        file_type=ext.lstrip("."),
        extracted_text=text,
        interview_id=interview_id,
        entry_id=entry_id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return {
        "id": rec.id,
        "filename": rec.filename,
        "file_type": rec.file_type,
        "interview_id": rec.interview_id,
        "entry_id": rec.entry_id,
        "extracted_chars": len(text or ""),
        "preview": (text or "")[:400],
    }
