"""ORM models — retailers, products, retailer_products, price_observations."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class Retailer(Base):
    __tablename__ = "retailers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    products: Mapped[list["RetailerProduct"]] = relationship(
        back_populates="retailer", cascade="all, delete-orphan"
    )


class Product(Base):
    """Canonical normalized product."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("brand", "name", "variant", "volume_ml", name="uq_canonical_product"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    variant: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    volume_ml: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    retailer_products: Mapped[list["RetailerProduct"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class RetailerProduct(Base):
    """A retailer's specific listing for a canonical product."""

    __tablename__ = "retailer_products"
    __table_args__ = (
        UniqueConstraint("retailer_id", "retailer_product_id", name="uq_retailer_listing"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    retailer_id: Mapped[int] = mapped_column(
        ForeignKey("retailers.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    retailer_product_id: Mapped[str] = mapped_column(String(120), nullable=False)
    retailer_product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    retailer: Mapped[Retailer] = relationship(back_populates="products")
    product: Mapped[Product] = relationship(back_populates="retailer_products")
    observations: Mapped[list["PriceObservation"]] = relationship(
        back_populates="retailer_product", cascade="all, delete-orphan"
    )


class PriceObservation(Base):
    """A single price snapshot. Append-only — never overwrite."""

    __tablename__ = "price_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    retailer_product_id: Mapped[int] = mapped_column(
        ForeignKey("retailer_products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    postcode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    store_identifier: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    regular_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    sale_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="AUD", nullable=False)
    available: Mapped[bool] = mapped_column(default=True, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    retailer_product: Mapped[RetailerProduct] = relationship(back_populates="observations")