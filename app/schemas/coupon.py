from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CouponItem(BaseModel):
    """FUNC-007-02: 쿠폰 목록 카드 한 건."""

    coupon_id: int
    name: str
    image_url: str | None
    point_price: int
    description: str | None

    model_config = {"from_attributes": True}


class CouponDetail(CouponItem):
    """FUNC-007-01: 쿠폰 상세 (클릭 후 구매 전 확인 화면)."""


class CouponPurchaseResponse(BaseModel):
    """FUNC-007-01: 쿠폰 구매 완료 응답 (바코드 포함)."""

    user_coupon_id: int
    coupon_id: int
    name: str
    barcode: str
    status: str
    purchased_at: datetime
    valid_until: datetime | None
    balance_after: int
