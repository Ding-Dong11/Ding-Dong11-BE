from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Store(Base):
    """database.md STORES (섹션 10) 1:1 매핑. geom/search_tsv 는 DB Generated 컬럼이라 ORM 매핑 제외."""

    __tablename__ = "stores"

    store_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    store_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    store_name: Mapped[str] = mapped_column(String(200), nullable=False)
    branch_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    small_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("category_small.small_code"), nullable=True
    )
    adong_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("adong.adong_code"), nullable=True
    )
    bdong_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("bdong.bdong_code"), nullable=True
    )
    industry_code: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("standard_industry.industry_code"), nullable=True
    )
    road_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    jibun_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class StoreQrCode(Base):
    """database.md STORE_QR_CODES (섹션 16) 1:1 매핑."""

    __tablename__ = "store_qr_codes"

    qr_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stores.store_id"), nullable=False
    )
    qr_token: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    reward_point: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    store: Mapped[Store] = relationship("Store", lazy="select")


class RewardVerification(Base):
    """database.md REWARD_VERIFICATIONS (섹션 17) 1:1 매핑.

    복합 FK (qr_id, store_id) → store_qr_codes(qr_id, store_id): 'QR이 해당 상가 소속' DB 강제.
    store_id 는 무결성용 의도적 비정규화 (database.md 섹션 17).
    """

    __tablename__ = "reward_verifications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["qr_id", "store_id"],
            ["store_qr_codes.qr_id", "store_qr_codes.store_id"],
            name="fk_reward_verifications_qr_store",
        ),
    )

    reward_verification_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    store_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    qr_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    awarded_point: Mapped[int] = mapped_column(Integer, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PointTransaction(Base):
    """database.md POINT_TRANSACTIONS (섹션 18) 1:1 매핑."""

    __tablename__ = "point_transactions"

    transaction_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    tx_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reward_verification_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("reward_verifications.reward_verification_id"),
        nullable=True,
    )
    user_coupon_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("user_coupons.user_coupon_id"), nullable=True
    )
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
