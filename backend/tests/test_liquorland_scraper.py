"""Liquorland adapter parser tests using saved fixtures."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.scrapers.liquorland import LiquorlandScraper

FIXTURE = Path(__file__).parent / "fixtures" / "liquorland_search_jack_daniels.html"


@pytest.mark.asyncio
async def test_liquorland_parses_fixture(monkeypatch):
    """Parse the captured Coles search page HTML and assert products emerge."""
    scraper = LiquorlandScraper()

    html = FIXTURE.read_text(encoding="utf-8")

    class FakeResponse:
        status_code = 200
        text = html

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None):
            return FakeResponse()

    monkeypatch.setattr("app.scrapers.liquorland.httpx.AsyncClient", FakeClient)

    results = await scraper.search("jack daniels", postcode="4000")
    assert len(results) == 5
    # First product — Whiskey 700ml @ $68, supplied by Liquorland
    r0 = results[0]
    assert r0.brand == "Jack Daniels"
    assert r0.name == "Whiskey 700ml"
    assert r0.volume_ml == 700
    assert r0.price == Decimal("68.00")
    assert r0.available is True
    assert r0.url.endswith("/product/8331431")
    assert r0.store_identifier == "liquorland"


@pytest.mark.asyncio
async def test_liquorland_1l_on_sale(monkeypatch):
    """The 1L Tennessee Whiskey is on special: now $80, was $91."""
    scraper = LiquorlandScraper()
    html = FIXTURE.read_text(encoding="utf-8")

    class FakeResponse:
        status_code = 200
        text = html

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None):
            return FakeResponse()

    monkeypatch.setattr("app.scrapers.liquorland.httpx.AsyncClient", FakeClient)

    results = await scraper.search("jack daniels", postcode="4000")
    onel = next(r for r in results if r.volume_ml == 1000)
    assert onel.name == "Tennessee Whiskey 1 Litre"
    assert onel.price == Decimal("80.00")
    assert onel.regular_price == Decimal("91.00")  # was > now => on sale
    assert onel.sale_price == Decimal("80.00")


@pytest.mark.asyncio
async def test_liquorland_missing_next_data(monkeypatch):
    """If the page has no __NEXT_DATA__, raise ScraperError."""
    from app.scrapers.base import ScraperError

    scraper = LiquorlandScraper()

    class FakeResponse:
        status_code = 200
        text = "<html>no next data</html>"

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None):
            return FakeResponse()

    monkeypatch.setattr("app.scrapers.liquorland.httpx.AsyncClient", FakeClient)

    with pytest.raises(ScraperError):
        await scraper.search("jack daniels")