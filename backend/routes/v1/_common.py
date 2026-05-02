"""Helpers shared across the /api/v1 endpoints."""
from __future__ import annotations
from datetime import datetime, timezone
from fastapi.responses import JSONResponse


DISCLAIMER = (
    "This information is based on approved expert knowledge and does not "
    "constitute professional advice."
)


def utc_now_iso() -> str:
    """ISO 8601 with trailing Z, the format the benchmark expects."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_or_none(dt) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message, "code": code})


# Benchmark-facing status names for KnowledgeEntry. Internally we use
# "pending_admin_review" because that's what John's interview pipeline writes;
# the benchmark spec calls that state "sme_approved". Translate at the API
# boundary in both directions.
INTERNAL_TO_EXTERNAL_STATUS = {
    "pending": "draft",
    "draft": "draft",
    "pending_review": "pending_review",
    "pending_admin_review": "sme_approved",
    "approved": "approved",
    "rejected": "rejected",
}

EXTERNAL_TO_INTERNAL_STATUS = {
    "draft": "pending",
    "pending_review": "pending_review",
    "sme_approved": "pending_admin_review",
    "approved": "approved",
    "rejected": "rejected",
}


def to_external_status(internal: str | None) -> str | None:
    if internal is None:
        return None
    return INTERNAL_TO_EXTERNAL_STATUS.get(internal, internal)


def to_internal_status(external: str | None) -> str | None:
    if external is None:
        return None
    return EXTERNAL_TO_INTERNAL_STATUS.get(external, external)
