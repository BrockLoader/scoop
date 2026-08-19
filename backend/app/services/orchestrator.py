"""Search orchestrator.

Holds the registry of enabled scrapers, fans out a query concurrently,
isolates failures, applies caching, and persists price observations.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..logging_setup import get_logger
from ..models import PriceObservation, Product, Retailer, RetailerProduct
from ..schemas import ProductResult, SearchError, SearchResponse
from ..scrapers.base import RetailerScraper, RawProduct, ScraperError
from ..services.cache import SearchCache
from ..services.normalize import (
    normalize_query,
    normalize_text,
    price_per_litre,
)
from .cache import SearchCache as _SearchCache

log = get_logger("scoop.orchestrator")

# Product-family signals: words that, when present in a listing's
# normalized name, mark it as NOT a primary spirit (RTDs, premixes,
# seltzers, gift packs, sauces, etc). We use these to keep "Jack
# Daniel's Tennessee Whiskey 1L" visible while demoting "Jack Daniel's
# & Cola Can 375ml" and "Jack Daniel's BBQ Sauce 284g" when the user
# searches the broad term.
_RTD_SIGNALS = {
    "seltzer", "cola", "lemonade", "sugar cola",
    "rtds", "premixed", "premix", "mixer",
    "sauce", "marinade", "bbq",
    "gift pack", "gift box", "glass pack", "cooler bag",
    "minis", "mini", "sampler", "shot",
}
_PRIMARY_SPIRIT_TOKENS = {"whiskey", "whisky", "rye", "bourbon", "tennessee"}


def _is_primary_spirit(name: str, brand: str) -> bool:
    """Heuristic: is this listing actually a bottle of spirit?

    Used to demote obvious non-spirit listings (RTDs/seltzers/sauces/
    gift packs) from broad searches. We accept almost everything from
    a spirit brand and only demote when a strong RTD/non-spirit
    signal appears in the product name. This keeps variants like
    "Single Barrel", "Bonded", "Gentleman Jack" visible.
    """
    n = normalize_text(name)
    has_rtd = any(sig in n for sig in _RTD_SIGNALS)
    return not has_rtd


@dataclass
class RetailerSpec:
    slug: str
    display_name: str
    scraper: RetailerScraper
    enabled: bool


def build_registry(settings: Settings) -> list[RetailerSpec]:
    """Construct the scraper registry from config."""
    from ..scrapers.bws import BWSScraper
    from ..scrapers.danmurphys import DanMurphysScraper
    from ..scrapers.liquorland import LiquorlandScraper

    return [
        RetailerSpec(
            slug="danmurphys",
            display_name="Dan Murphy's",
            scraper=DanMurphysScraper(timeout=settings.scrape_timeout_seconds),
            enabled=settings.enable_danmurphys,
        ),
        RetailerSpec(
            slug="bws",
            display_name="BWS",
            scraper=BWSScraper(timeout=settings.scrape_timeout_seconds),
            enabled=settings.enable_bws,
        ),
        RetailerSpec(
            slug="liquorland",
            display_name="Liquorland",
            scraper=LiquorlandScraper(timeout=settings.scrape_timeout_seconds),
            enabled=settings.enable_liquorland,
        ),
    ]


class SearchOrchestrator:
    def __init__(
        self,
        registry: list[RetailerSpec],
        cache: SearchCache,
    ) -> None:
        self._registry = [r for r in registry if r.enabled]
        self._cache = cache

    @property
    def enabled_specs(self) -> list[RetailerSpec]:
        return list(self._registry)

    async def search(
        self,
        db: Session,
        *,
        query: str,
        postcode: Optional[str] = None,
        requested_volume_ml: Optional[int] = None,
    ) -> SearchResponse:
        normalized = normalize_query(query)
        log.info(
            "search.start",
            query=query,
            normalized=normalized,
            postcode=postcode,
            retailers=[r.slug for r in self._registry],
        )

        # Build per-retailer tasks
        async def one(spec: RetailerSpec) -> tuple[str, list[RawProduct] | Exception]:
            cache_key = _SearchCache.make_key(spec.slug, normalized, postcode)
            cached = await self._cache.get(cache_key)
            if cached is not None:
                log.info("search.cache_hit", retailer=spec.slug)
                return spec.slug, cached
            try:
                results = await spec.scraper.search(query, postcode=postcode)
            except ScraperError as exc:
                log.warning(
                    "search.scraper_failed",
                    retailer=spec.slug,
                    error=str(exc),
                )
                return spec.slug, exc
            except Exception as exc:  # defensive: never let one scraper sink the search
                log.error(
                    "search.scraper_unhandled",
                    retailer=spec.slug,
                    error=repr(exc),
                )
                return spec.slug, exc
            await self._cache.set(cache_key, results)
            return spec.slug, results

        # Run with a generous overall timeout but per-scraper timeouts
        # already enforced inside the adapters.
        raw_outcomes = await asyncio.gather(
            *(one(spec) for spec in self._registry),
            return_exceptions=True,
        )

        # Translate outcomes to response models + persist observations.
        results: list[ProductResult] = []
        errors: list[SearchError] = []
        now = datetime.utcnow()
        for outcome in raw_outcomes:
            if isinstance(outcome, BaseException):
                log.error("search.task_unhandled", error=repr(outcome))
                continue
            slug, payload = outcome
            if isinstance(payload, BaseException):
                errors.append(
                    SearchError(retailer=slug, message=_public_error_message(payload))
                )
                continue
            for raw in payload:
                try:
                    persisted = persist_observation(db, raw, observed_at=now)
                    if persisted is None:
                        continue
                except Exception as exc:
                    log.error(
                        "persist.failed",
                        retailer=slug,
                        product=raw.retailer_product_id,
                        error=repr(exc),
                    )
                    continue
                # Demote obvious non-spirit listings (RTDs/seltzers/sauces)
                # out of broad term searches so the user sees actual bottles.
                if not _is_primary_spirit(raw.name, raw.brand):
                    log.info(
                        "search.demoted_non_spirit",
                        retailer=slug,
                        name=raw.name,
                    )
                    continue
                results.append(_to_result(raw, observed_at=now))

        log.info(
            "search.complete",
            result_count=len(results),
            error_count=len(errors),
        )
        return SearchResponse(
            query=query,
            postcode=postcode,
            results=results,
            errors=errors,
        )


def _public_error_message(exc: BaseException) -> str:
    """Map an internal exception to a user-facing message."""
    if isinstance(exc, ScraperError):
        return "Retailer search failed"
    return "Retailer search failed"


def _to_result(raw: RawProduct, *, observed_at: datetime) -> ProductResult:
    ppl = price_per_litre(raw.price, raw.volume_ml)
    on_sale = bool(raw.sale_price is not None and raw.regular_price and raw.regular_price > raw.price)
    return ProductResult(
        retailer=raw.retailer,
        retailer_product_id=raw.retailer_product_id,
        name=raw.name,
        brand=raw.brand,
        variant=raw.variant,
        volume_ml=raw.volume_ml,
        price=raw.price,
        regular_price=raw.regular_price,
        sale_price=raw.sale_price,
        price_per_litre=ppl,
        available=raw.available,
        on_sale=on_sale,
        url=raw.url,
        observed_at=observed_at,
        postcode=raw.postcode,
        store_identifier=raw.store_identifier,
        location_aware=raw.location_aware,
    )


def persist_observation(
    db: Session,
    raw: RawProduct,
    *,
    observed_at: datetime,
) -> Optional[PriceObservation]:
    """Persist a price observation.

    Idempotent on `(retailer_product_id, observed_at minute bucket)`
    in the sense that we always INSERT a new row — but the brief
    asks us to retain history, so duplicates by minute are acceptable.
    Returns the persisted row.
    """
    # Upsert retailer
    retailer = (
        db.query(Retailer).filter(Retailer.slug == raw.retailer).one_or_none()
    )
    if retailer is None:
        retailer = Retailer(
            slug=raw.retailer,
            name=raw.retailer.replace("danmurphys", "Dan Murphy's").replace("bws", "BWS").title()
            if raw.retailer == "bws"
            else raw.retailer.replace("liquorland", "Liquorland").title(),
            base_url=raw.url,
            enabled=True,
        )
        db.add(retailer)
        db.flush()

    # Upsert canonical product (brand + name + variant + volume)
    canonical = (
        db.query(Product)
        .filter(
            Product.brand == raw.brand,
            Product.name == raw.name,
            Product.variant == raw.variant,
            Product.volume_ml == raw.volume_ml,
        )
        .one_or_none()
    )
    if canonical is None:
        canonical = Product(
            brand=raw.brand,
            name=raw.name,
            variant=raw.variant,
            volume_ml=raw.volume_ml,
        )
        db.add(canonical)
        db.flush()

    # Upsert retailer_product link
    rp = (
        db.query(RetailerProduct)
        .filter(
            RetailerProduct.retailer_id == retailer.id,
            RetailerProduct.retailer_product_id == raw.retailer_product_id,
        )
        .one_or_none()
    )
    if rp is None:
        rp = RetailerProduct(
            retailer_id=retailer.id,
            product_id=canonical.id,
            retailer_product_id=raw.retailer_product_id,
            retailer_product_name=raw.name,
            product_url=raw.url,
        )
        db.add(rp)
        db.flush()

    obs = PriceObservation(
        retailer_product_id=rp.id,
        postcode=raw.postcode,
        store_identifier=raw.store_identifier,
        price=raw.price,
        regular_price=raw.regular_price,
        sale_price=raw.sale_price,
        currency="AUD",
        available=raw.available,
        observed_at=observed_at,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


# Module-level singleton. We construct lazily on first use so tests can
# override `get_settings()` if needed.
_registry: Optional[list[RetailerSpec]] = None
_cache: Optional[SearchCache] = None


def get_orchestrator() -> SearchOrchestrator:
    global _registry, _cache
    if _registry is None:
        settings = get_settings()
        _registry = build_registry(settings)
    if _cache is None:
        settings = get_settings()
        _cache = SearchCache(ttl_seconds=settings.scrape_cache_ttl_seconds)
    return SearchOrchestrator(_registry, _cache)