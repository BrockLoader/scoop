"""Pydantic schemas — request and response shapes."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class SearchError(BaseModel):
    retailer: str
    message: str


class ProductResult(BaseModel):
    retailer: str
    retailer_product_id: str
    name: str
    brand: str
    variant: Optional[str] = None
    volume_ml: Optional[int] = None
    price: Decimal
    regular_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    price_per_litre: Optional[Decimal] = None
    available: bool = True
    on_sale: bool = False
    url: str
    observed_at: datetime
    # location context used for this observation
    postcode: Optional[str] = None
    store_identifier: Optional[str] = None
    # when we can't trust the price was actually store-specific
    location_aware: bool = True


class SearchResponse(BaseModel):
    query: str
    postcode: Optional[str] = None
    results: list[ProductResult] = Field(default_factory=list)
    errors: list[SearchError] = Field(default_factory=list)


class RetailerOut(BaseModel):
    id: int
    name: str
    slug: str
    base_url: str
    enabled: bool

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    version: str
    db: str