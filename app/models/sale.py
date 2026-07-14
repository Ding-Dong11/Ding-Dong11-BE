from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SaleStore(Base):
    """database.md SALE_STORES (섹션 19) 1:1 매핑. geom 은 DB Generated 컬럼이라 ORM 매핑 제외."""

    __tablename__ = "sale_stores"

    sale_store_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    store_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stores.store_id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    adong_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("adong.adong_code"), nullable=True
    )
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)

    hours: Mapped[list[SaleStoreHour]] = relationship(
        "SaleStoreHour", back_populates="sale_store", lazy="select"
    )
    products: Mapped[list[SaleProduct]] = relationship(
        "SaleProduct", back_populates="sale_store", lazy="select"
    )


class SaleStoreHour(Base):
    """database.md SALE_STORE_HOURS (섹션 20) 1:1 매핑."""

    __tablename__ = "sale_store_hours"
    __table_args__ = (
        CheckConstraint(
            "day_of_week IN ('MON','TUE','WED','THU','FRI','SAT','SUN')",
            name="ck_sale_store_hours_day",
        ),
    )

    hour_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sale_store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sale_stores.sale_store_id"), nullable=False
    )
    day_of_week: Mapped[str] = mapped_column(String(10), nullable=False)
    open_time: Mapped[time] = mapped_column(Time, nullable=False)
    close_time: Mapped[time] = mapped_column(Time, nullable=False)

    sale_store: Mapped[SaleStore] = relationship("SaleStore", back_populates="hours")


class SaleProduct(Base):
    """database.md SALE_PRODUCTS (섹션 21) 1:1 매핑. search_tsv 는 DB Generated 컬럼이라 ORM 매핑 제외."""

    __tablename__ = "sale_products"
    __table_args__ = (
        CheckConstraint("sale_price <= original_price", name="ck_sale_products_price"),
        CheckConstraint("stock_quantity >= 0", name="ck_sale_products_stock"),
        CheckConstraint(
            "status IN ('ON_SALE','SOLD_OUT','EXPIRED')", name="ck_sale_products_status"
        ),
    )

    sale_product_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sale_store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sale_stores.sale_store_id"), nullable=False
    )
    small_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("category_small.small_code"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    original_price: Mapped[int] = mapped_column(Integer, nullable=False)
    sale_price: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sale_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ON_SALE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    sale_store: Mapped[SaleStore] = relationship("SaleStore", back_populates="products")


class SaleSubscription(Base):
    """database.md SALE_SUBSCRIPTIONS (섹션 22) 1:1 매핑."""

    __tablename__ = "sale_subscriptions"

    subscription_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    sale_store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sale_stores.sale_store_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
