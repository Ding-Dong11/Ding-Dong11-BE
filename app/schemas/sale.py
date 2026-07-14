from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, computed_field


# ── 공통 헬퍼 ───────────────────────────────────────────────────────────────

def _effective_status(status: str, stock_quantity: int, sale_deadline: datetime) -> str:
    """DB status + 재고/마감 실시간 보정 상태."""
    from datetime import UTC
    now = datetime.now(UTC)
    if sale_deadline < now:
        return "EXPIRED"
    if stock_quantity == 0:
        return "SOLD_OUT"
    return status


# ── FUNC-004-01: 피드 ───────────────────────────────────────────────────────

class SaleProductCard(BaseModel):
    """피드/상점 상세 내 상품 카드."""

    sale_product_id: int
    sale_store_id: int
    store_name: str
    name: str
    original_price: int
    sale_price: int
    discount_rate: float
    stock_quantity: int
    sale_deadline: datetime
    effective_status: str
    small_code: str | None


class FeedResponse(BaseModel):
    """FUNC-004-01: 세일 피드 페이지."""

    items: list[SaleProductCard]
    total: int
    page: int
    size: int
    has_next: bool


# ── FUNC-004-01: 관심 등록 ──────────────────────────────────────────────────

class SubscribeResponse(BaseModel):
    subscribed: bool
    sale_store_id: int


# ── FUNC-004-02: 지도 마커 ──────────────────────────────────────────────────

class SaleStoreMarker(BaseModel):
    """FUNC-004-02: 세일 상점 지도 마커."""

    sale_store_id: int
    name: str
    longitude: Decimal
    latitude: Decimal
    is_expiring_soon: bool


# ── FUNC-004-03: 상점 상세 ──────────────────────────────────────────────────

class SaleStoreHourSchema(BaseModel):
    day_of_week: str
    open_time: time
    close_time: time

    model_config = {"from_attributes": True}


class SaleStoreDetail(BaseModel):
    """FUNC-004-03: 세일 상점 상세 (영업시간 + 활성 상품 목록)."""

    sale_store_id: int
    name: str
    longitude: Decimal
    latitude: Decimal
    hours: list[SaleStoreHourSchema]
    products: list[SaleProductCard]


# ── FUNC-004-03: 상품 상세 ──────────────────────────────────────────────────

class SaleProductDetail(BaseModel):
    """FUNC-004-03: 상품 상세 — 재고·마감 실시간."""

    sale_product_id: int
    sale_store_id: int
    store_name: str
    name: str
    original_price: int
    sale_price: int
    discount_rate: float
    stock_quantity: int
    sale_deadline: datetime
    effective_status: str
    small_code: str | None
