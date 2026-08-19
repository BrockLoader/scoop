"""GET /api/health and GET /health."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from .. import __version__
from ..schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
@router.get("/api/health", response_model=HealthResponse)
async def health(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:  # noqa: BLE001 — health endpoint must report any state
        db_status = f"down: {exc.__class__.__name__}"
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        version=__version__,
        db=db_status,
    )