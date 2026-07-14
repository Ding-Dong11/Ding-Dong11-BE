from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.coupon import Coupon, UserCoupon


class CouponRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── FUNC-007-02: 쿠폰 목록 ─────────────────────────────────────────────────

    def list_active(self) -> list[Coupon]:
        """활성 상태인 구매 가능 쿠폰 전체 조회."""
        stmt = select(Coupon).where(Coupon.is_active.is_(True)).order_by(Coupon.coupon_id)
        return list(self.db.scalars(stmt))

    def get_by_id(self, coupon_id: int) -> Coupon | None:
        return self.db.get(Coupon, coupon_id)

    # ── FUNC-007-01: 쿠폰 구매 ─────────────────────────────────────────────────

    def create_user_coupon(
        self,
        *,
        user_id: int,
        coupon_id: int,
        barcode: str,
        valid_until: datetime,
    ) -> UserCoupon:
        uc = UserCoupon(
            user_id=user_id,
            coupon_id=coupon_id,
            barcode=barcode,
            status="UNUSED",
            valid_until=valid_until,
        )
        self.db.add(uc)
        self.db.flush()
        return uc
