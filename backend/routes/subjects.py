from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


class SubjectCreate(BaseModel):
    name: str
    description: str | None = None
    sme_id: int | None = None
    expertise: str | None = None


class SubjectOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


@router.get("", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    return db.query(models.Subject).order_by(models.Subject.name).all()


@router.post("", response_model=SubjectOut)
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Subject name is required")
    existing = db.query(models.Subject).filter(models.Subject.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subject with that name already exists")
    s = models.Subject(name=name, description=payload.description)
    db.add(s)
    db.flush()

    if payload.sme_id is not None:
        sme = db.query(models.Profile).filter(
            models.Profile.id == payload.sme_id, models.Profile.role == "sme"
        ).first()
        if not sme:
            raise HTTPException(status_code=404, detail="SME not found")
        sme.subjects = list(sme.subjects) + [s]
        # Capture the expertise scope on the SME profile so the directory and
        # the SME agent prompt have something to display.
        if payload.expertise and payload.expertise.strip():
            sme.expertise_area = payload.expertise.strip()

    db.commit()
    db.refresh(s)
    return s
