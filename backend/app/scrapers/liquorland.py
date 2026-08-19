"""Liquorland / First Choice Liquor adapter.

Coles group. Strategy: fetch the Next.js SSR'd search page and parse
the embedded `__NEXT_DATA__` JSON. That gives us a complete result
list with prices, sale pricing, comparables, volumes, availability,
and Liquorland branding context — all without needing the BFF
endpoint directly.

The page does some client-side enrichment after hydration, but for
the POC the server-rendered data is sufficient.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Optional

import httpx

from ..services.normalize import (
    parse_price,
    parse_volume_ml,
    price_per_litre,
)
from .base import RawProduct, RetailerScraper, ScraperError

_SEARCH_URL = "https://www.coles.com.au/search/products"
_NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
    re.DOTALL,
)


class LiquorlandScraper(RetailerScraper):
    slug = "liquorland"
    display_name = "Liquorland"
    base_url = "https://www.liquorland.com.au"

    def __init__(self, *, timeout: float = 15.0, user_agent: str = "ScoopPOC/0.1") -> None:
        self._timeout = timeout
        self._user_agent = user_agent

    async def search(
        self,
        query: str,
        postcode: Optional[str] = None,
    ) -> list[RawProduct]:
        params = {"q": query}
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-AU,en;q=0.9",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                resp = await client.get(_SEARCH_URL, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise ScraperError(f"timeout fetching {_SEARCH_URL}", cause=exc) from exc
        except httpx.HTTPError as exc:
            raise ScraperError(f"http error: {exc}", cause=exc) from exc

        if resp.status_code != 200:
            raise ScraperError(f"unexpected status {resp.status_code}")

        m = _NEXT_DATA.search(resp.text)
        if not m:
            raise ScraperError("could not find __NEXT_DATA__ in page")

        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError as exc:
            raise ScraperError("invalid __NEXT_DATA__ JSON", cause=exc) from exc

        results = (
            data.get("props", {})
            .get("pageProps", {})
            .get("searchResults", {})
            .get("results", [])
        )

        out: list[RawProduct] = []
        for entry in results:
            if not isinstance(entry, dict) or entry.get("_type") != "PRODUCT":
                continue
            rp = _to_raw_product(entry, postcode=postcode)
            if rp is not None:
                out.append(rp)
        return out


def _to_raw_product(entry: dict, *, postcode: Optional[str]) -> Optional[RawProduct]:
    """Translate one Coles product dict into a RawProduct.

    Returns None if the entry lacks a parseable price.
    """
    description = entry.get("description") or ""
    # Description carries the volume: "JACK DANIELS WHISKEY 700ML:EA"
    volume_ml = parse_volume_ml(description) or parse_volume_ml(entry.get("size", ""))

    pricing = entry.get("pricing") or {}
    now = parse_price(pricing.get("now"))
    if now is None:
        return None
    was = parse_price(pricing.get("was")) if pricing.get("was") else None
    on_sale = bool(was and was > now)

    product_id = entry.get("id")
    if not product_id:
        return None

    # Build the product page URL. Coles routes product pages by id.
    url = f"https://www.coles.com.au/product/{product_id}"

    # Determine if this is actually a Liquorland-supplied product.
    # The page surfaces both Coles-owned and Liquorland-supplied stock.
    # We treat the entry as Liquorland if internalDescription mentions
    # "Liquorland" OR the merchandiseHeir maps there.
    internal_desc = (entry.get("internalDescription") or "")
    is_liquorland = "liquorland" in internal_desc.lower() or _is_liquorland_heir(
        entry.get("onlineHeirs")
    )

    # If it's not a Liquorland listing, we still return it under the
    # Liquorland adapter name — but the user can filter on retailer
    # later. For the POC, the store ID identifies the source.
    return RawProduct(
        retailer="liquorland",
        retailer_product_id=f"coles-{product_id}",
        name=(entry.get("name") or "").strip(),
        brand=(entry.get("brand") or "").strip(),
        variant=None,
        volume_ml=volume_ml,
        price=now,
        regular_price=was if on_sale else None,
        sale_price=now if on_sale else None,
        available=bool(entry.get("availability", True)),
        url=url,
        postcode=postcode,
        store_identifier="liquorland" if is_liquorland else "coles-online",
        location_aware=False,  # SSR is store-agnostic for online-only delivery
        extra={
            "comparable": (pricing.get("comparable") or "").strip(),
            "is_liquorland_supplied": is_liquorland,
        },
    )


def _is_liquorland_heir(heirs) -> bool:
    if not isinstance(heirs, list):
        return False
    for h in heirs:
        if isinstance(h, dict):
            if "liquorland" in (h.get("subCategory") or "").lower():
                return True
    return False