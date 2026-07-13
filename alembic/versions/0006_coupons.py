"""coupons / user_coupons (쿠폰 카탈로그 · 보유 쿠폰)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coupons",
        sa.Column("coupon_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=True),
        # point_price: 포인트 = 금액 1:1 (database.md)
        sa.Column("point_price", sa.Integer, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("idx_coupons_is_active", "coupons", ["is_active"])
    op.execute(
        """
        ALTER TABLE coupons ADD COLUMN search_tsv tsvector
          GENERATED ALWAYS AS (to_tsvector('simple', coalesce(name,''))) STORED
        """
    )
    op.execute("CREATE INDEX idx_coupons_search ON coupons USING GIN (search_tsv)")

    op.create_table(
        "user_coupons",
        sa.Column("user_coupon_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("coupon_id", sa.BigInteger, sa.ForeignKey("coupons.coupon_id"), nullable=False),
        sa.Column("barcode", sa.String(100), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="UNUSED"),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('UNUSED','USED','EXPIRED')", name="ck_user_coupons_status"),
    )
    op.create_index("idx_user_coupons_user_status", "user_coupons", ["user_id", "status"])
    op.create_index("idx_user_coupons_coupon", "user_coupons", ["coupon_id"])


def downgrade() -> None:
    op.drop_table("user_coupons")
    op.drop_table("coupons")
