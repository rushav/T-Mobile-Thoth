"""In-memory session store for /api/v1/query multi-turn flow.

A session captures what the previous response_type was so a follow-up message
sent under the same session_id can be interpreted in context. The two states
that matter for routing are:

- "awaiting_clarification": last response asked the user to disambiguate
  between subjects. The next message is treated as the disambiguator and
  combined with the original question for re-classification.
- "answered": last response was a grounded answer to a specific subject. The
  next message, if it doesn't classify cleanly on its own, can be treated as
  a follow-up routed to that same subject.

Wiped by /api/v1/system/reset and /api/v1/system/purge.
"""
from __future__ import annotations
from threading import Lock
from typing import Any
import uuid

_lock = Lock()
_sessions: dict[str, dict[str, Any]] = {}


def new_session_id() -> str:
    return str(uuid.uuid4())


def get(session_id: str) -> dict[str, Any] | None:
    if not session_id:
        return None
    with _lock:
        return _sessions.get(session_id)


def set(session_id: str, **fields: Any) -> None:
    if not session_id:
        return
    with _lock:
        existing = _sessions.get(session_id, {})
        existing.update(fields)
        _sessions[session_id] = existing


def clear_one(session_id: str) -> None:
    with _lock:
        _sessions.pop(session_id, None)


def clear_all() -> None:
    with _lock:
        _sessions.clear()
