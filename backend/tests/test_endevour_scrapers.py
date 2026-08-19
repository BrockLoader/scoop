"""BWS / Dan Murphy's adapter parser tests — using nested-shape fixtures."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.scrapers.bws import BWSScraper
from app.scrapers.danmurphys import DanMurphysScraper


# Real BWS response shape (nested `Products`). This is a slimmed version
# of the live `/apis/ui/Search/Products` response captured against BWS.
BWS_FIXTURE = {
    "Products": [
        {
            "Name": " Jack Daniel's Old No.7<br>Tennessee Whiskey 1l  ",
            "PackDefaultStockCode": 27390,
            "PackParentStockCode": 27390,
            "Products": [
                {
                    "Stockcode": 27390,
                    "Name": "Jack Daniel's Old No.7 Tennessee Whiskey 1l",
                    "UrlFriendlyName": "jack-daniel-s-old-no-7-tennessee-whiskey-1l",
                    "Description": " Jack Daniel's Old No.7<br>Tennessee Whiskey 1l  1L",
                    "BrandName": "Jack Daniel's",
                    "PackageSize": "1L",
                    "Price": 80,
                    "WasPrice": 91,
                    "IsOnSpecial": True,
                    "IsAvailable": True,
                    "IsPurchasable": True,
                },
            ],
        },
        {
            "Name": " Jack Daniel's Tennessee Whiskey<br>700ml  ",
            "PackDefaultStockCode": 1234,
            "PackParentStockCode": 1234,
            "Products": [
                {
                    "Stockcode": 1234,
                    "Name": "Jack Daniel's Whiskey 700ml",
                    "UrlFriendlyName": "jack-daniel-s-whiskey-700ml",
                    "Description": "Jack Daniel's Whiskey 700ml",
                    "BrandName": "Jack Daniel's",
                    "PackageSize": "700ml",
                    "Price": 68,
                    "WasPrice": 0,
                    "IsOnSpecial": False,
                    "IsAvailable": True,
                    "IsPurchasable": True,
                },
            ],
        },
    ]
}


DM_FIXTURE = {
    "Products": [
        {
            "Name": "Jack Daniel's Old No.7 1L",
            "PackDefaultStockCode": 99,
            "Products": [
                {
                    "Stockcode": 99,
                    "Name": "Jack Daniel's Old No.7 Tennessee Whiskey 1L",
                    "Description": "Jack Daniel's Old No.7 Tennessee Whiskey 1L 1L",
                    "PackageSize": "1L",
                    "Prices": {
                        "singleprice": {
                            "Message": "each",
                            "Value": 78.0,
                            "PackType": "Bottle",
                        }
                    },
                    "IsOnSpecial": False,
                    "IsAvailable": True,
                    "IsPurchasable": True,
                    "AdditionalDetails": [
                        {"Name": "webbrandname", "Value": "Jack Daniel's"},
                    ],
                },
            ],
        },
        {
            "Name": "Jack Daniel's Whiskey 700ml",
            "Products": [
                {
                    "Stockcode": 100,
                    "Name": "Jack Daniel's Whiskey 700ml",
                    "Description": "Jack Daniel's Whiskey 700ml 700ml",
                    "PackageSize": "700ml",
                    "Prices": {"singleprice": {"Value": 65.0, "PackType": "Bottle"}},
                    "IsOnSpecial": False,
                    "IsAvailable": True,
                    "IsPurchasable": True,
                    "AdditionalDetails": [
                        {"Name": "webbrandname", "Value": "Jack Daniel's"},
                    ],
                },
            ],
        },
    ]
}


class FakeResponse:
    def __init__(self, status_code, body_dict) -> None:
        self.status_code = status_code
        self._body = body_dict

    def json(self):
        import json
        return json.loads(json.dumps(self._body))


class FakeClient:
    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[tuple] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append((url, json, headers))
        # Detect retailer from origin header
        origin = (headers or {}).get("Origin") or (headers or {}).get("origin") or ""
        if "bws" in origin:
            return FakeResponse(200, BWS_FIXTURE)
        return FakeResponse(200, DM_FIXTURE)


@pytest.mark.asyncio
async def test_bws_parses_nested_products(monkeypatch):
    scraper = BWSScraper()
    monkeypatch.setattr("app.scrapers.bws.httpx.AsyncClient", FakeClient)

    results = await scraper.search("jack daniels", postcode="4000")
    assert len(results) == 2
    r0 = results[0]
    assert r0.brand == "Jack Daniel's"
    assert r0.name == "Jack Daniel's Old No.7 Tennessee Whiskey 1l"
    assert r0.volume_ml == 1000
    assert r0.price == Decimal("80.00")
    assert r0.regular_price == Decimal("91.00")  # WasPrice > Price => on sale
    assert r0.sale_price == Decimal("80.00")
    assert r0.url.endswith("/jack-daniel-s-old-no-7-tennessee-whiskey-1l")
    assert r0.location_aware is True


@pytest.mark.asyncio
async def test_bws_no_special(monkeypatch):
    """When IsOnSpecial is false and WasPrice is 0, regular_price stays None."""
    scraper = BWSScraper()
    monkeypatch.setattr("app.scrapers.bws.httpx.AsyncClient", FakeClient)

    results = await scraper.search("jack daniels", postcode="4000")
    r1 = next(r for r in results if r.volume_ml == 700)
    assert r1.price == Decimal("68.00")
    assert r1.regular_price is None
    assert r1.sale_price is None


@pytest.mark.asyncio
async def test_danmurphys_parses_prices_singleprice(monkeypatch):
    scraper = DanMurphysScraper()
    monkeypatch.setattr("app.scrapers.danmurphys.httpx.AsyncClient", FakeClient)

    results = await scraper.search("jack daniels", postcode="4000")
    assert len(results) == 2
    r0 = results[0]
    assert r0.brand == "Jack Daniel's"
    assert r0.volume_ml == 1000
    assert r0.price == Decimal("78.00")
    assert r0.location_aware is True


@pytest.mark.asyncio
async def test_danmurphys_no_price_returns_no_products(monkeypatch):
    """If Prices.singleprice.Value is missing, the entry is skipped."""
    scraper = DanMurphysScraper()

    class NoPriceClient(FakeClient):
        async def post(self, url, json=None, headers=None):
            broken = {"Products": [{"Products": [{"Stockcode": 1, "Name": "x"}]}]}
            return FakeResponse(200, broken)

    monkeypatch.setattr("app.scrapers.danmurphys.httpx.AsyncClient", NoPriceClient)

    results = await scraper.search("jack daniels", postcode="4000")
    assert results == []