from fastapi import APIRouter
from ._common import utc_now_iso

router = APIRouter(prefix="/api/v1", tags=["v1-health"])


@router.get("/health")
def health():
    return {"status": "healthy", "timestamp": utc_now_iso()}
