from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Identity, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Coupon(Base):
    """database.md COUPONS (섹션 23) 1:1 매핑. FUNC-007-02."""

    __tablename__ = "coupons"

    coupon_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    point_price: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    user_coupons: Mapped[list[UserCoupon]] = relationship("UserCoupon", back_populates="coupon", lazy="noload")


class UserCoupon(Base):
    """database.md USER_COUPONS (섹션 24) 1:1 매핑. FUNC-007-01, 008-02."""

    __tablename__ = "user_coupons"

    user_coupon_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    coupon_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("coupons.coupon_id"), nullable=False)
    barcode: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="UNUSED")
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    coupon: Mapped[Coupon] = relationship("Coupon", back_populates="user_coupons", lazy="select")
