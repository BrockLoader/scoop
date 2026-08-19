"""Orchestrator-level tests: failure isolation, caching, persistence.

These use an in-memory SQLite database and stub scrapers so they're
fast and deterministic.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import PriceObservation
from app.scrapers.base import RawProduct, RetailerScraper, ScraperError
from app.services.cache import SearchCache
from app.services.orchestrator import RetailerSpec, SearchOrchestrator


def _make_db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng, autoflush=False, autocommit=False, future=True)()


class _OkScraper(RetailerScraper):
    slug = "fake_ok"
    display_name = "Fake OK"
    base_url = "https://example.com"

    def __init__(self, products):
        self._products = products

    async def search(self, query, postcode=None):
        return list(self._products)


class _FailScraper(RetailerScraper):
    slug = "fake_fail"
    display_name = "Fake Fail"
    base_url = "https://example.com"

    async def search(self, query, postcode=None):
        raise ScraperError("simulated retailer down")


def _raw(retailer, pid, price, vol=None, available=True, name=None):
    return RawProduct(
        retailer=retailer,
        retailer_product_id=pid,
        name=name or f"Test {pid}",
        brand="TestBrand",
        variant=None,
        volume_ml=vol,
        price=Decimal(price),
        regular_price=None,
        sale_price=None,
        available=available,
        url=f"https://example.com/{pid}",
        postcode="4000",
        store_identifier=None,
        location_aware=True,
    )


@pytest.mark.asyncio
async def test_failure_isolation_one_succeeds_one_fails():
    db = _make_db()
    cache = SearchCache(ttl_seconds=60)
    registry = [
        RetailerSpec(
            slug="fake_ok",
            display_name="OK",
            scraper=_OkScraper([_raw("fake_ok", "1", "80.00", vol=1000, name="Test Tennessee Whiskey 1L")]),
            enabled=True,
        ),
        RetailerSpec(
            slug="fake_fail",
            display_name="Fail",
            scraper=_FailScraper(),
            enabled=True,
        ),
    ]
    orch = SearchOrchestrator(registry, cache)
    resp = await orch.search(db, query="jack daniels", postcode="4000")
    assert len(resp.results) == 1
    assert resp.results[0].retailer == "fake_ok"
    assert len(resp.errors) == 1
    assert resp.errors[0].retailer == "fake_fail"
    assert resp.errors[0].message == "Retailer search failed"


@pytest.mark.asyncio
async def test_persists_observations_with_correct_volume():
    db = _make_db()
    cache = SearchCache(ttl_seconds=60)
    registry = [
        RetailerSpec(
            slug="fake_ok",
            display_name="OK",
            scraper=_OkScraper([_raw("fake_ok", "abc", "80.00", vol=1000, name="Test Tennessee Whiskey 1L")]),
            enabled=True,
        ),
    ]
    orch = SearchOrchestrator(registry, cache)
    await orch.search(db, query="jack daniels", postcode="4000")
    obs = db.query(PriceObservation).all()
    assert len(obs) == 1
    assert obs[0].price == Decimal("80.00")
    assert obs[0].postcode == "4000"


@pytest.mark.asyncio
async def test_cache_prevents_second_call():
    """Second identical search uses the cache and does not invoke the scraper."""
    db = _make_db()
    cache = SearchCache(ttl_seconds=60)
    called = {"n": 0}

    class CountingScraper(RetailerScraper):
        slug = "counter"
        display_name = "Counter"
        base_url = "https://example.com"

        async def search(self, query, postcode=None):
            called["n"] += 1
            return [_raw("counter", "1", "80.00", vol=1000)]

    registry = [
        RetailerSpec(slug="counter", display_name="Counter",
                     scraper=CountingScraper(), enabled=True),
    ]
    orch = SearchOrchestrator(registry, cache)
    await orch.search(db, query="jack daniels", postcode="4000")
    await orch.search(db, query="jack daniels", postcode="4000")
    assert called["n"] == 1


@pytest.mark.asyncio
async def test_demote_rtd_listings():
    """RTDs/seltzers/premixed should not appear in broad spirit searches."""
    from app.services.orchestrator import _is_primary_spirit
    # These ARE primary spirits — keep them
    assert _is_primary_spirit("Jack Daniel's Old No.7 Tennessee Whiskey 1L", "Jack Daniel's")
    assert _is_primary_spirit("Jack Daniel's Single Barrel 700ml", "Jack Daniel's")
    assert _is_primary_spirit("Jack Daniel's Tennessee Honey Whiskey 700ml", "Jack Daniel's")
    # RTDs / sauces — drop them
    assert not _is_primary_spirit("Jack Daniel's & Cola Can 375ml", "Jack Daniel's")
    assert not _is_primary_spirit("Jack Daniel's Tennessee Seltzer Blood Orange 330ml", "Jack Daniel's")
    assert not _is_primary_spirit("Jack Daniel's Original BBQ Sauce 284g", "Jack Daniel's")
    assert not _is_primary_spirit("Jack Daniel's Gift Box Set", "Jack Daniel's")