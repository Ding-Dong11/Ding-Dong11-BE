"""sale_stores / sale_store_hours / sale_products / sale_subscriptions (마감할인 세일 마트)

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sale_stores",
        sa.Column("sale_store_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("store_id", sa.BigInteger, sa.ForeignKey("stores.store_id"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("adong_code", sa.String(10), sa.ForeignKey("adong.adong_code"), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
    )
    op.create_index("idx_sale_stores_store", "sale_stores", ["store_id"])
    op.create_index("idx_sale_stores_adong", "sale_stores", ["adong_code"])
    op.execute(
        """
        ALTER TABLE sale_stores ADD COLUMN geom geometry(Point, 4326)
          GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude::float8, latitude::float8), 4326)) STORED
        """
    )
    op.execute("CREATE INDEX idx_sale_stores_geom ON sale_stores USING GIST (geom)")

    op.create_table(
        "sale_store_hours",
        sa.Column("hour_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "sale_store_id", sa.BigInteger, sa.ForeignKey("sale_stores.sale_store_id"), nullable=False
        ),
        sa.Column("day_of_week", sa.String(10), nullable=False),
        sa.Column("open_time", sa.Time, nullable=False),
        sa.Column("close_time", sa.Time, nullable=False),
        sa.CheckConstraint(
            "day_of_week IN ('MON','TUE','WED','THU','FRI','SAT','SUN')",
            name="ck_sale_store_hours_day",
        ),
    )
    op.create_index(
        "idx_sale_store_hours_store_day", "sale_store_hours", ["sale_store_id", "day_of_week"]
    )

    op.create_table(
        "sale_products",
        sa.Column("sale_product_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "sale_store_id", sa.BigInteger, sa.ForeignKey("sale_stores.sale_store_id"), nullable=False
        ),
        sa.Column("small_code", sa.String(10), sa.ForeignKey("category_small.small_code"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("original_price", sa.Integer, nullable=False),
        sa.Column("sale_price", sa.Integer, nullable=False),
        sa.Column("stock_quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sale_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ON_SALE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("sale_price <= original_price", name="ck_sale_products_price"),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_sale_products_stock"),
        sa.CheckConstraint(
            "status IN ('ON_SALE','SOLD_OUT','EXPIRED')", name="ck_sale_products_status"
        ),
    )
    op.create_index("idx_sale_products_store", "sale_products", ["sale_store_id"])
    op.create_index("idx_sale_products_deadline", "sale_products", ["status", "sale_deadline"])
    op.create_index("idx_sale_products_category", "sale_products", ["small_code"])
    op.execute(
        """
        ALTER TABLE sale_products ADD COLUMN search_tsv tsvector
          GENERATED ALWAYS AS (to_tsvector('simple', coalesce(name,''))) STORED
        """
    )
    op.execute("CREATE INDEX idx_sale_products_search ON sale_products USING GIN (search_tsv)")

    op.create_table(
        "sale_subscriptions",
        sa.Column("subscription_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column(
            "sale_store_id", sa.BigInteger, sa.ForeignKey("sale_stores.sale_store_id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_sale_subs", "sale_subscriptions", ["user_id", "sale_store_id"]
    )
    op.create_index("idx_sale_subs_store", "sale_subscriptions", ["sale_store_id"])


def downgrade() -> None:
    op.drop_table("sale_subscriptions")
    op.drop_table("sale_products")
    op.drop_table("sale_store_hours")
    op.drop_table("sale_stores")
