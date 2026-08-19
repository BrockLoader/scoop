"""FastAPI entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .logging_setup import configure_logging, get_logger
from .routers import health, retailers, search

log = get_logger("scoop.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info(
        "scoop.startup",
        version=__version__,
        default_postcode=settings.default_postcode,
        enabled=[
            r.slug
            for r in [
                type("S", (), {"slug": "danmurphys"})(),
                type("S", (), {"slug": "bws"})(),
                type("S", (), {"slug": "liquorland"})(),
            ]
            if getattr(settings, f"enable_{r.slug}", True)
        ],
    )
    yield
    log.info("scoop.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Scoop",
        description="Australian Liquor Price Search — POC",
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(search.router)
    app.include_router(retailers.router)
    return app


app = create_app()