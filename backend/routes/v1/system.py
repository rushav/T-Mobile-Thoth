"""POST /api/v1/system/{purge,reset}.

- purge: nuclear reset. Drop every table, delete every Chroma collection, wipe
  uploaded files, and clear in-memory session state. Leaves the system in the
  same state as a fresh checkout (no seed data).
- reset: clear /api/v1/query session state only. SME profiles, interviews,
  knowledge entries, and ChromaDB content all stay.
"""
from __future__ import annotations
import shutil
from pathlib import Path

from fastapi import APIRouter

from config import UPLOADS_DIR
from database import Base, engine, init_db
from services import sessions
import vector_store

router = APIRouter(prefix="/api/v1/system", tags=["v1-system"])


def _purge_chroma() -> None:
    """Best-effort wipe of every Chroma collection.

    list_collections() returns Collection objects in older Chroma versions and
    raw names in newer ones — handle both."""
    client = getattr(vector_store, "_client", None)
    if client is None:
        return
    try:
        listing = client.list_collections()
    except Exception:
        return
    for item in listing or []:
        name = getattr(item, "name", None) or (item if isinstance(item, str) else None)
        if not name:
            continue
        try:
            client.delete_collection(name=name)
        except Exception:
            pass


def _purge_uploads() -> None:
    p = Path(UPLOADS_DIR)
    if not p.exists():
        return
    for child in p.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        except Exception:
            pass


@router.post("/purge")
def purge():
    # 1. SQL: drop and recreate every table.
    Base.metadata.drop_all(bind=engine)
    init_db()
    # 2. Vector store: delete every collection.
    _purge_chroma()
    # 3. Uploaded files on disk.
    _purge_uploads()
    # 4. In-memory query sessions.
    sessions.clear_all()
    return {"status": "purged", "message": "All data has been deleted"}


@router.post("/reset")
def reset():
    sessions.clear_all()
    return {"status": "reset", "message": "Session state cleared. Knowledge base preserved."}
