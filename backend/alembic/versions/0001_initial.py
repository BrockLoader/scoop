"""initial schema: retailers, products, retailer_products, price_observations

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-19 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retailers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("slug", sa.String(length=64), nullable=False, unique=True),
        sa.Column("base_url", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("brand", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("variant", sa.String(length=120), nullable=True),
        sa.Column("volume_ml", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("brand", "name", "variant", "volume_ml", name="uq_canonical_product"),
    )

    op.create_table(
        "retailer_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "retailer_id",
            sa.Integer(),
            sa.ForeignKey("retailers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("retailer_product_id", sa.String(length=120), nullable=False),
        sa.Column("retailer_product_name", sa.String(length=255), nullable=False),
        sa.Column("product_url", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("retailer_id", "retailer_product_id", name="uq_retailer_listing"),
    )

    op.create_table(
        "price_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "retailer_product_id",
            sa.Integer(),
            sa.ForeignKey("retailer_products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("postcode", sa.String(length=10), nullable=True),
        sa.Column("store_identifier", sa.String(length=120), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("regular_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("sale_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="AUD"),
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_price_observations_retailer_product_id",
        "price_observations",
        ["retailer_product_id"],
    )
    op.create_index(
        "ix_price_observations_observed_at",
        "price_observations",
        ["observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_price_observations_observed_at", table_name="price_observations")
    op.drop_index(
        "ix_price_observations_retailer_product_id", table_name="price_observations"
    )
    op.drop_table("price_observations")
    op.drop_table("retailer_products")
    op.drop_table("products")
    op.drop_table("retailers")