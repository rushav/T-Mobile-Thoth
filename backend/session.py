"""Minimal in-memory 'session' store for current profile.

PoC only — no real auth. The frontend sends X-Profile-Id on requests.
"""
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
import models


def get_current_profile(
    x_profile_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.Profile | None:
    if not x_profile_id:
        return None
    try:
        pid = int(x_profile_id)
    except ValueError:
        return None
    return db.query(models.Profile).filter(models.Profile.id == pid).first()


def require_current_profile(
    profile: models.Profile | None = Depends(get_current_profile),
) -> models.Profile:
    if profile is None:
        raise HTTPException(status_code=401, detail="No profile selected")
    return profile
