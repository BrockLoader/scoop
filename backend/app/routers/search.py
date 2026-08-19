"""GET /search — the primary search endpoint."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..logging_setup import get_logger
from ..schemas import SearchResponse
from ..services.orchestrator import get_orchestrator

router = APIRouter(prefix="", tags=["search"])
log = get_logger("scoop.api.search")


@router.get("/search", response_model=SearchResponse)
@router.get("/api/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=120, description="Product search query"),
    postcode: Optional[str] = Query(
        None, min_length=3, max_length=10, description="Australian postcode"
    ),
    volume_ml: Optional[int] = Query(
        None,
        ge=1,
        le=10000,
        description="Optional exact volume filter in ml (e.g. 1000 for 1L)",
    ),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SearchResponse:
    postcode = postcode or settings.default_postcode
    orchestrator = get_orchestrator()
    return await orchestrator.search(
        db,
        query=q,
        postcode=postcode,
        requested_volume_ml=volume_ml,
    )