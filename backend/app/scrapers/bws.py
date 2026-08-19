"""BWS adapter.

Endeavour Group BWS. The search endpoint is `POST /apis/ui/Search/Products`
on `api.bws.com.au` with a JSON body. The response shape is:

{
  "Products": [
    {
      "Name": "...",
      "PackDefaultStockcode": ...,
      "Products": [
        {
          "Stockcode": 27390,
          "Name": "Jack Daniel's Old No.7 Tennessee Whiskey 1l",
          "UrlFriendlyName": "jack-daniel-s-old-no-7-tennessee-whiskey-1l",
          "Description": "...",
          "BrandName": "Jack Daniel's",
          "PackageSize": "1L",
          "Price": 80,
          "WasPrice": 91,
          "IsOnSpecial": true,
          "IsAvailable": true,
          "IsPurchasable": true,
          "DisplayQuantity": 1,
          ...
        }
      ]
    },
    ...
  ]
}

Each top-level entry in `Products` is a pack (multi-buy); its nested
`Products` array contains one or more retail variants. We flatten by
emitting one RawProduct per nested variant.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Optional

import httpx

from ..services.normalize import parse_price, parse_volume_ml
from .base import RawProduct, RetailerScraper, ScraperError

_BASE = "https://api.bws.com.au/apis/ui"
_SEARCH_PATH = "/Search/Products"


class BWSScraper(RetailerScraper):
    slug = "bws"
    display_name = "BWS"
    base_url = "https://www.bws.com.au"

    def __init__(self, *, timeout: float = 15.0, user_agent: str = "ScoopPOC/0.1") -> None:
        self._timeout = timeout
        self._user_agent = user_agent

    async def search(
        self,
        query: str,
        postcode: Optional[str] = None,
    ) -> list[RawProduct]:
        payload = {
            "searchTerm": query,
            "pageSize": 40,
            "pageNumber": 1,
            "sortBy": "Search_Relevance",
        }
        if postcode:
            payload["fulfilmentPostcode"] = postcode

        headers = {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
            "Origin": self.base_url,
            "Referer": self.base_url + "/search?q=" + query.replace(" ", "+"),
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(_BASE + _SEARCH_PATH, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ScraperError(f"timeout fetching BWS search", cause=exc) from exc
        except httpx.HTTPError as exc:
            raise ScraperError(f"http error: {exc}", cause=exc) from exc

        if resp.status_code != 200:
            raise ScraperError(f"unexpected status {resp.status_code}")

        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise ScraperError("invalid JSON", cause=exc) from exc

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


def _to_raw(entry: dict, *, postcode: Optional[str], base_url: str) -> Optional[RawProduct]:
    stockcode = entry.get("Stockcode") or entry.get("stockcode")
    if not stockcode:
        return None

    name = (entry.get("Name") or entry.get("name") or "").strip()
    if not name:
        return None
    brand = (entry.get("BrandName") or entry.get("brand") or "").strip()
    url_slug = entry.get("UrlFriendlyName") or entry.get("urlFriendlyName") or ""
    url = entry.get("Url") or (
        f"{base_url}/product/{url_slug}" if url_slug else f"{base_url}/product/{stockcode}"
    )

    description = entry.get("Description") or entry.get("description") or ""
    package_size = entry.get("PackageSize") or entry.get("packageSize") or ""
    volume_ml = parse_volume_ml(description) or parse_volume_ml(package_size)

    price_now = entry.get("Price") or entry.get("price")
    was_price = entry.get("WasPrice") or entry.get("wasPrice") or 0
    now = parse_price(price_now)
    if now is None:
        return None
    was = parse_price(was_price)
    on_sale = bool(entry.get("IsOnSpecial")) or bool(was and was > now)

    available = bool(
        entry.get("IsAvailable", True) and entry.get("IsPurchasable", True)
    )

    return RawProduct(
        retailer="bws",
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
        extra={"url_slug": url_slug},
    )