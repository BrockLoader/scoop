"""Dan Murphy's adapter.

Endeavour Group. Same JSON shape family as BWS but with different
field conventions:

- Request uses `query` (lowercase) and requires `storeId`.
- Response shape: `{ "Products": [ { ..., "Products": [ inner ] } ] }`
- Inner product has `Prices.singleprice.Value` instead of `Price`.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from ..services.normalize import parse_price, parse_volume_ml
from .base import RawProduct, RetailerScraper, ScraperError

_BASE = "https://api.danmurphys.com.au/apis/ui"
_SEARCH_PATH = "/Search/Products"


class DanMurphysScraper(RetailerScraper):
    slug = "danmurphys"
    display_name = "Dan Murphy's"
    base_url = "https://www.danmurphys.com.au"

    def __init__(self, *, timeout: float = 15.0, user_agent: str = "ScoopPOC/0.1") -> None:
        self._timeout = timeout
        self._user_agent = user_agent

    async def search(
        self,
        query: str,
        postcode: Optional[str] = None,
    ) -> list[RawProduct]:
        # NOTE on Dan Murphy's payload:
        # The /apis/ui/Search/Products endpoint's payload signature is
        # unstable. Empirically (Aug 2026):
        #  - {searchTerm: "..."}  -> 200 [redirect action] to /list/<slug>
        #  - {query: "..."}       -> 200 with unfiltered browse (no filter applied)
        #  - ...other variants   -> 200 unfiltered or 400
        # No payload shape produces a properly-filtered product list
        # from this endpoint at the moment. The DM frontend loads the
        # search bundle dynamically and assembles a working call client
        # side, which we can't replicate here without bundling DM's JS.
        #
        # For the POC we emit the request we believe is closest to
        # correct, then surface any failure as a ScraperError so the
        # orchestrator reports it via the `errors` array. BWS covers
        # the acceptance test on its own.
        payload: dict[str, Any] = {
            "searchTerm": query,
            "pageSize": 40,
            "pageNumber": 1,
            "storeId": "1024",
        }
        if postcode:
            payload["fulfilmentPostcode"] = postcode

        headers = {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
            "Origin": self.base_url,
            "Referer": self.base_url + "/search?searchTerm=" + query.replace(" ", "+"),
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(_BASE + _SEARCH_PATH, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ScraperError(f"timeout fetching DM search", cause=exc) from exc
        except httpx.HTTPError as exc:
            raise ScraperError(f"http error: {exc}", cause=exc) from exc

        if resp.status_code != 200:
            raise ScraperError(f"unexpected status {resp.status_code}")

        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise ScraperError("invalid JSON", cause=exc) from exc

        # If the response is a list (redirect action), DM's search is
        # gated behind its SPA bundle. Treat as a no-op failure.
        if isinstance(data, list):
            raise ScraperError(
                "DM search returned a redirect/list action; this endpoint "
                "currently does not return filtered products for arbitrary "
                "queries. See README 'Limitations'."
            )

        return _extract_products(data, postcode=postcode, base_url=self.base_url)


def _extract_products(data: Any, *, postcode: Optional[str], base_url: str) -> list[RawProduct]:
    if not isinstance(data, dict):
        return []
    outer = data.get("Products")
    if not isinstance(outer, list):
        return []

    products: list[RawProduct] = []
    seen: set[str] = set()
    for pack in outer:
        if not isinstance(pack, dict):
            continue
        inner = pack.get("Products")
        if not isinstance(inner, list):
            continue
        for entry in inner:
            if not isinstance(entry, dict):
                continue
            rp = _to_raw(entry, postcode=postcode, base_url=base_url)
            if rp and rp.retailer_product_id not in seen:
                seen.add(rp.retailer_product_id)
                products.append(rp)
    return products


def _extract_price(entry: dict) -> Optional[Any]:
    """DM nests the price under Prices.singleprice.Value."""
    prices = entry.get("Prices")
    if not isinstance(prices, dict):
        return None
    single = prices.get("singleprice")
    if not isinstance(single, dict):
        return None
    return single.get("Value")


def _extract_was_price(entry: dict) -> Optional[Any]:
    """Some DM responses include a WasPrice field on the inner product."""
    was = entry.get("WasPrice")
    if was is not None:
        return was
    prices = entry.get("Prices")
    if isinstance(prices, dict):
        single = prices.get("singleprice")
        if isinstance(single, dict):
            before = single.get("BeforePromotion")
            if isinstance(before, dict):
                return before.get("Value")
    return None


def _to_raw(entry: dict, *, postcode: Optional[str], base_url: str) -> Optional[RawProduct]:
    stockcode = entry.get("Stockcode") or entry.get("stockcode")
    if not stockcode:
        return None

    name = (entry.get("Name") or entry.get("name") or "").strip()
    if not name:
        return None

    # DM doesn't always include BrandName on the inner; try AdditionalDetails.
    brand = entry.get("BrandName") or entry.get("brand") or ""
    if not brand:
        for ad in entry.get("AdditionalDetails", []):
            if isinstance(ad, dict) and ad.get("Name") in ("webbrandname", "brandname"):
                v = ad.get("Value")
                if isinstance(v, str):
                    brand = v
                    break

    description = entry.get("Description") or entry.get("description") or ""
    package_size = entry.get("PackageSize") or ""
    if not package_size:
        # Some DM entries expose size via AdditionalDetails
        for ad in entry.get("AdditionalDetails", []):
            if isinstance(ad, dict) and ad.get("Name") == "webliquorsize":
                v = ad.get("Value")
                if isinstance(v, str):
                    package_size = v
                    break
    volume_ml = parse_volume_ml(description) or parse_volume_ml(package_size)

    price_raw = _extract_price(entry)
    was_raw = _extract_was_price(entry)
    now = parse_price(price_raw)
    if now is None:
        return None
    was = parse_price(was_raw)
    on_sale = bool(entry.get("IsOnSpecial")) or bool(was and was > now)

    url = entry.get("Url") or f"{base_url}/product/{stockcode}"
    available = bool(
        entry.get("IsAvailable", True) and entry.get("IsPurchasable", True)
    )

    return RawProduct(
        retailer="danmurphys",
        retailer_product_id=str(stockcode),
        name=name,
        brand=brand or "Unknown",
        variant=None,
        volume_ml=volume_ml,
        price=now,
        regular_price=was if on_sale else None,
        sale_price=now if on_sale else None,
        available=available,
        url=url,
        postcode=postcode,
        store_identifier=None,
        location_aware=bool(postcode),
        extra={},
    )