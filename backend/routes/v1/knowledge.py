"""Benchmark-shaped knowledge entry endpoints.

Statuses on the wire use the benchmark vocabulary (draft / sme_approved /
approved / rejected). Internally we still use our own names — see
_common.to_external_status / to_internal_status for the mapping.

V1 pipeline endpoints (PUT /{id}, POST /{id}/approve) operate on V1KnowledgeEntry
(string IDs like ke_xxx). Legacy endpoints use old KnowledgeEntry (integer IDs).
"""
from __future__ import annotations
from datetime import datetime

from fastapi import APIRouter, Depends, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

import models
import vector_store
from database import get_db

from ._common import (
    error,
    iso_or_none,
    to_external_status,
    to_internal_status,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["v1-knowledge"])


# ── V1 pipeline models ────────────────────────────────────────────────────────

class EntryUpdate(BaseModel):
    content: str


class RejectBody(BaseModel):
    reason: str | None = None


# ── V1 pipeline endpoints (string IDs: ke_xxx) ────────────────────────────────

@router.put("/{entry_id}")
def update_v1_entry(entry_id: str, payload: EntryUpdate, db: Session = Depends(get_db)):
    """Edit a V1 knowledge entry's content (benchmark SME-edit flow)."""
    entry = db.query(models.V1KnowledgeEntry).filter(models.V1KnowledgeEntry.entry_id == entry_id).first()
    if not entry:
        return error(404, "NOT_FOUND", f"Knowledge entry {entry_id} not found")
    entry.content = payload.content
    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    return {
        "entry_id": entry.entry_id,
        "sme_id": entry.sme_id,
        "topic": entry.topic,
        "status": entry.status,
        "content": entry.content,
        "sources": entry.sources or {},
        "created_at": iso_or_none(entry.created_at),
        "updated_at": iso_or_none(entry.updated_at),
    }


@router.post("/{entry_id}/approve")
def sme_approve_entry(entry_id: str, db: Session = Depends(get_db)):
    """SME approves a V1 knowledge entry (draft → sme_approved)."""
    entry = db.query(models.V1KnowledgeEntry).filter(models.V1KnowledgeEntry.entry_id == entry_id).first()
    if not entry:
        return error(404, "NOT_FOUND", f"Knowledge entry {entry_id} not found")
    if entry.status != "draft":
        return JSONResponse(
            status_code=409,
            content={"error": "Entry must be in draft status to approve", "code": "INVALID_STATE_TRANSITION"},
        )
    entry.status = "sme_approved"
    entry.approved_at = datetime.utcnow()
    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    return {
        "entry_id": entry.entry_id,
        "status": entry.status,
        "approved_at": iso_or_none(entry.approved_at),
    }


# ── Legacy endpoints (integer IDs: old KnowledgeEntry) ───────────────────────

def _entry_payload(entry: models.KnowledgeEntry) -> dict:
    """Render a KnowledgeEntry in the shape the benchmark expects."""
    sme_name = entry.contributor.name if entry.contributor else None
    return {
        "entry_id": entry.id,
        "sme_id": entry.contributor_id,
        "topic": entry.title,
        "status": to_external_status(entry.status),
        "content": entry.content,
        "sources": [
            {
                "entry_id": entry.id,
                "sme_name": sme_name,
                "topic": entry.title,
            }
        ],
        "created_at": iso_or_none(entry.created_at),
        "updated_at": iso_or_none(entry.updated_at or entry.created_at),
    }


@router.get("")
def list_entries(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.KnowledgeEntry)
    if status:
        internal = to_internal_status(status)
        q = q.filter(models.KnowledgeEntry.status == internal)
    entries = q.order_by(models.KnowledgeEntry.id.asc()).all()
    return {"entries": [_entry_payload(e) for e in entries]}


@router.get("/{entry_id}")
def get_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
    if not entry:
        return error(404, "NOT_FOUND", f"Knowledge entry {entry_id} not found")
    return _entry_payload(entry)


def _find_or_create_subject_for_topic(db: Session, topic: str) -> models.Subject:
    """V1 entries don't carry a subject_id; we map topic 1:1 to a Subject row so
    the classifier and the existing per-subject ChromaDB collections still work
    for the V1 pipeline. Idempotent: returns the existing Subject if a row with
    the same name already exists."""
    subj = db.query(models.Subject).filter(models.Subject.name == topic).first()
    if subj:
        return subj
    subj = models.Subject(name=topic, description=f"V1 SME knowledge: {topic}")
    db.add(subj)
    db.flush()
    return subj


@router.post("/{entry_id}/admin-approve")
def admin_approve(entry_id: str, db: Session = Depends(get_db)):
    """Final admin approval. Accepts both V1 (string ke_xxx) and legacy
    (integer) entry IDs — dispatches on the prefix so we can keep one URL."""
    # ── V1 SME-pipeline path ──────────────────────────────────────────────
    if entry_id.startswith("ke_"):
        v1 = db.query(models.V1KnowledgeEntry).filter(models.V1KnowledgeEntry.entry_id == entry_id).first()
        if not v1:
            return error(404, "NOT_FOUND", f"Knowledge entry {entry_id} not found")
        if v1.status != "sme_approved":
            return error(
                409,
                "INVALID_STATE_TRANSITION",
                f"Entry is in state '{v1.status}', expected 'sme_approved'",
            )
        subj = _find_or_create_subject_for_topic(db, v1.topic)
        v1.status = "approved"
        v1.approved_at = datetime.utcnow()
        v1.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(v1)
        # Index the synthesized content so /api/v1/query can retrieve it.
        vector_store.add_v1_entry(subj.id, v1.entry_id, v1.sme_id, v1.topic, v1.content)
        return {
            "entry_id": v1.entry_id,
            "status": "approved",
            "admin_approved_at": iso_or_none(v1.approved_at),
        }

    # ── Legacy path (integer IDs) ─────────────────────────────────────────
    try:
        legacy_id = int(entry_id)
    except ValueError:
        return error(404, "NOT_FOUND", f"Knowledge entry {entry_id} not found")
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == legacy_id).first()
    if not entry:
        return error(404, "NOT_FOUND", f"Knowledge entry {entry_id} not found")
    if entry.status != "pending_admin_review":
        return error(
            409,
            "INVALID_STATE_TRANSITION",
            f"Entry is in state '{to_external_status(entry.status)}', expected 'sme_approved'",
        )
    entry.status = "approved"
    entry.approved_at = datetime.utcnow()
    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    vector_store.add_entry(entry.subject_id, entry.id, entry.title, entry.content)
    return {
        "entry_id": entry.id,
        "status": "approved",
        "admin_approved_at": iso_or_none(entry.approved_at),
    }


@router.post("/{entry_id}/reject")
def reject(entry_id: str, body: RejectBody = Body(default=RejectBody()), db: Session = Depends(get_db)):
    """Reject an entry. Accepts both V1 (string) and legacy (integer) IDs."""
    # ── V1 path ───────────────────────────────────────────────────────────
    if entry_id.startswith("ke_"):
        v1 = db.query(models.V1KnowledgeEntry).filter(models.V1KnowledgeEntry.entry_id == entry_id).first()
        if not v1:
            return error(404, "NOT_FOUND", f"Knowledge entry {entry_id} not found")
        if v1.status == "rejected":
            return error(409, "INVALID_STATE_TRANSITION", "Entry is already rejected")
        prior_status = v1.status
        v1.status = "rejected"
        v1.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(v1)
        # If it was already in Chroma (admin-approved before being rejected),
        # tear it back out. We need a subject_id — find by topic, no-op if missing.
        if prior_status == "approved":
            subj = db.query(models.Subject).filter(models.Subject.name == v1.topic).first()
            if subj:
                vector_store.remove_v1_entry(subj.id, v1.entry_id)
        return {
            "entry_id": v1.entry_id,
            "status": "rejected",
            "rejected_at": iso_or_none(v1.updated_at),
        }

    # ── Legacy path ───────────────────────────────────────────────────────
    try:
        legacy_id = int(entry_id)
    except ValueError:
        return error(404, "NOT_FOUND", f"Knowledge entry {entry_id} not found")
    entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == legacy_id).first()
    if not entry:
        return error(404, "NOT_FOUND", f"Knowledge entry {entry_id} not found")
    if entry.status == "rejected":
        return error(409, "INVALID_STATE_TRANSITION", "Entry is already rejected")
    entry.status = "rejected"
    if body.reason is not None:
        entry.rejection_reason = body.reason
    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    vector_store.remove_entry(entry.subject_id, entry.id)
    return {
        "entry_id": entry.id,
        "status": "rejected",
        "rejected_at": iso_or_none(entry.updated_at),
    }
