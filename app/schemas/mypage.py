from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PointResponse(BaseModel):
    """FUNC-008-01: 보유 포인트 정보."""

    user_id: int
    point_balance: int

    model_config = {"from_attributes": True}


class UserCouponItem(BaseModel):
    """FUNC-008-02: 보유 쿠폰 보관함 목록 카드 한 건."""

    user_coupon_id: int
    coupon_id: int
    name: str
    image_url: str | None
    status: str
    purchased_at: datetime
    valid_until: datetime | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_coupon(cls, uc: object) -> "UserCouponItem":
        return cls(
            user_coupon_id=uc.user_coupon_id,  # type: ignore[attr-defined]
            coupon_id=uc.coupon_id,  # type: ignore[attr-defined]
            name=uc.coupon.name,  # type: ignore[attr-defined]
            image_url=uc.coupon.image_url,  # type: ignore[attr-defined]
            status=uc.status,  # type: ignore[attr-defined]
            purchased_at=uc.purchased_at,  # type: ignore[attr-defined]
            valid_until=uc.valid_until,  # type: ignore[attr-defined]
        )


class UserCouponDetail(UserCouponItem):
    """FUNC-008-02: 보유 쿠폰 상세 (바코드 포함)."""

    barcode: str
    description: str | None

    @classmethod
    def from_orm_with_coupon(cls, uc: object) -> "UserCouponDetail":  # type: ignore[override]
        return cls(
            user_coupon_id=uc.user_coupon_id,  # type: ignore[attr-defined]
            coupon_id=uc.coupon_id,  # type: ignore[attr-defined]
            name=uc.coupon.name,  # type: ignore[attr-defined]
            image_url=uc.coupon.image_url,  # type: ignore[attr-defined]
            status=uc.status,  # type: ignore[attr-defined]
            purchased_at=uc.purchased_at,  # type: ignore[attr-defined]
            valid_until=uc.valid_until,  # type: ignore[attr-defined]
            barcode=uc.barcode,  # type: ignore[attr-defined]
            description=uc.coupon.description,  # type: ignore[attr-defined]
        )
