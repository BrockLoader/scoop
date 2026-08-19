"""Common retailer interface.

Adapters live in this package and inherit from `RetailerScraper`.
The rest of the application consumes normalized `RawProduct` objects
and does not care how each retailer obtained them.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class RawProduct:
    """A single retailer listing before canonical-product mapping.

    Attributes:
        retailer: retailer slug ("danmurphys", "bws", "liquorland")
        retailer_product_id: retailer's own ID/SKU
        name: display name as shown on the listing
        brand: brand label
        variant: variant label (e.g. "Old No. 7") if known
        volume_ml: normalized volume in millilitres
        price: current price in AUD
        regular_price: pre-sale price if on special, else None
        sale_price: current promotional price if on special, else None
        available: stock status
        url: canonical product page URL
        postcode: store location context used
        store_identifier: optional store-specific identifier
        location_aware: True if the price reflects the postcode; False
            if we could not obtain location-specific pricing.
        extra: free-form metadata for adapters (not serialized).
    """

    retailer: str
    retailer_product_id: str
    name: str
    brand: str
    variant: Optional[str]
    volume_ml: Optional[int]
    price: Decimal
    regular_price: Optional[Decimal]
    sale_price: Optional[Decimal]
    available: bool
    url: str
    postcode: Optional[str]
    store_identifier: Optional[str]
    location_aware: bool
    extra: dict = field(default_factory=dict)


class RetailerScraper(abc.ABC):
    """A retailer adapter.

    Adapters MUST NOT throw on transient failures. On failure they
    raise `ScraperError` (or a subclass) so the orchestrator can
    isolate the failure and still return other retailers' results.
    """

    slug: str
    display_name: str
    base_url: str

    @abc.abstractmethod
    async def search(
        self,
        query: str,
        postcode: Optional[str] = None,
    ) -> list[RawProduct]:
        ...


class ScraperError(Exception):
    """Adapter failed. Subclass for granular handling."""

    def __init__(self, message: str, *, cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.__cause__ = cause


class RetailerDisabled(ScraperError):
    """Adapter is disabled in config."""


class RetailerTimeout(ScraperError):
    """Adapter timed out."""