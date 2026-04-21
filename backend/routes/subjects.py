from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


class SubjectCreate(BaseModel):
    name: str
    description: str | None = None


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
    existing = db.query(models.Subject).filter(models.Subject.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subject with that name already exists")
    s = models.Subject(name=payload.name.strip(), description=payload.description)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s
