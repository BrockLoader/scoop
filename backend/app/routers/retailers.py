"""GET /retailers — list enabled retailers."""
from __future__ import annotations

from fastapi import APIRouter

from ..schemas import RetailerOut
from ..services.orchestrator import get_orchestrator

router = APIRouter(prefix="", tags=["retailers"])


@router.get("/retailers", response_model=list[RetailerOut])
@router.get("/api/retailers", response_model=list[RetailerOut])
async def list_retailers() -> list[RetailerOut]:
    """List the retailers currently enabled in the orchestrator registry."""
    orchestrator = get_orchestrator()
    out: list[RetailerOut] = []
    for spec in orchestrator.enabled_specs:
        out.append(
            RetailerOut(
                id=0,  # not yet persisted; 0 is a placeholder
                name=spec.display_name,
                slug=spec.slug,
                base_url=spec.scraper.base_url,
                enabled=spec.enabled,
            )
        )
    return out