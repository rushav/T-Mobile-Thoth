from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


class ProfileCreate(BaseModel):
    name: str
    role: str  # user | sme | admin
    expertise_area: str | None = None
    subject_ids: list[int] | None = None


class ProfileOut(BaseModel):
    id: int
    name: str
    role: str
    expertise_area: str | None = None
    subject_ids: list[int] = []

    class Config:
        from_attributes = True


def _serialize(p: models.Profile) -> ProfileOut:
    return ProfileOut(
        id=p.id,
        name=p.name,
        role=p.role,
        expertise_area=p.expertise_area,
        subject_ids=[s.id for s in p.subjects],
    )


@router.post("", response_model=ProfileOut)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    if payload.role not in ("user", "sme", "admin"):
        raise HTTPException(status_code=400, detail="role must be user, sme, or admin")
    p = models.Profile(
        name=payload.name.strip(),
        role=payload.role,
        expertise_area=payload.expertise_area,
    )
    db.add(p)
    db.flush()

    if payload.role == "sme" and payload.subject_ids:
        subjects = db.query(models.Subject).filter(models.Subject.id.in_(payload.subject_ids)).all()
        p.subjects = subjects

    db.commit()
    db.refresh(p)
    return _serialize(p)


@router.get("", response_model=list[ProfileOut])
def list_profiles(role: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Profile)
    if role:
        q = q.filter(models.Profile.role == role)
    return [_serialize(p) for p in q.order_by(models.Profile.name).all()]


class LoginPayload(BaseModel):
    profile_id: int


@router.post("/login", response_model=ProfileOut)
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    p = db.query(models.Profile).filter(models.Profile.id == payload.profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _serialize(p)


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    p = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _serialize(p)
