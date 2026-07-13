"""store_qr_codes / reward_verifications / point_transactions (리워드 QR · 포인트 원장)

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_qr_codes",
        sa.Column("qr_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("store_id", sa.BigInteger, sa.ForeignKey("stores.store_id"), nullable=False),
        sa.Column("qr_token", sa.String(200), nullable=False, unique=True),
        sa.Column("reward_point", sa.Integer, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    # 상가당 활성 QR 1건 (database.md)
    op.execute(
        "CREATE UNIQUE INDEX uq_store_qr_active ON store_qr_codes(store_id) WHERE is_active = true"
    )
    # REWARD_VERIFICATIONS 복합 FK 대상: (qr_id, store_id) 유일키
    op.create_unique_constraint("uq_store_qr_pair", "store_qr_codes", ["qr_id", "store_id"])

    op.create_table(
        "reward_verifications",
        sa.Column("reward_verification_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.user_id"), nullable=False),
        # 의도적 비정규화: (qr_id, store_id) 복합 FK 로 "QR이 해당 상가 소속"을 DB 강제 (database.md)
        sa.Column("store_id", sa.BigInteger, nullable=False),
        sa.Column("qr_id", sa.BigInteger, nullable=False),
        sa.Column("awarded_point", sa.Integer, nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["qr_id", "store_id"],
            ["store_qr_codes.qr_id", "store_qr_codes.store_id"],
            name="fk_reward_verifications_qr_store",
        ),
    )
    op.create_index("idx_reward_user_time", "reward_verifications", ["user_id", sa.text("verified_at DESC")])
    op.create_index("idx_reward_store", "reward_verifications", ["store_id"])

    op.create_table(
        "point_transactions",
        sa.Column("transaction_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("tx_type", sa.String(20), nullable=False),
        sa.Column(
            "reward_verification_id",
            sa.BigInteger,
            sa.ForeignKey("reward_verifications.reward_verification_id"),
            nullable=True,
        ),
        sa.Column(
            "user_coupon_id", sa.BigInteger, sa.ForeignKey("user_coupons.user_coupon_id"), nullable=True
        ),
        # balance_after: 파생 스냅샷, 원장 변경과 동일 트랜잭션에서 갱신 (database.md)
        sa.Column("balance_after", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount <> 0", name="ck_point_tx_amount_nonzero"),
        sa.CheckConstraint(
            "tx_type IN ('REWARD_EARN','COUPON_REDEEM')", name="ck_point_tx_type"
        ),
        sa.CheckConstraint(
            "(tx_type = 'REWARD_EARN' AND reward_verification_id IS NOT NULL AND user_coupon_id IS NULL) OR "
            "(tx_type = 'COUPON_REDEEM' AND user_coupon_id IS NOT NULL AND reward_verification_id IS NULL)",
            name="ck_point_tx_source_exclusive",
        ),
    )
    op.create_index(
        "idx_point_tx_user_time", "point_transactions", ["user_id", sa.text("created_at DESC")]
    )
    op.create_index(
        "idx_point_tx_reward_verification", "point_transactions", ["reward_verification_id"]
    )
    op.create_index("idx_point_tx_user_coupon", "point_transactions", ["user_coupon_id"])


def downgrade() -> None:
    op.drop_table("point_transactions")
    op.drop_table("reward_verifications")
    op.drop_table("store_qr_codes")
