from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.coupon import Coupon, UserCoupon


class CouponRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── FUNC-007-02: 쿠폰 목록 ─────────────────────────────────────────────────

    def list_active(
        self,
        *,
        q: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
    ) -> list[Coupon]:
        """활성 쿠폰 조회. q=이름/설명 키워드, min/max_price=포인트 범위 필터."""
        stmt = select(Coupon).where(Coupon.is_active.is_(True))
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                Coupon.name.ilike(pattern) | Coupon.description.ilike(pattern)
            )
        if min_price is not None:
            stmt = stmt.where(Coupon.point_price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Coupon.point_price <= max_price)
        return list(self.db.scalars(stmt.order_by(Coupon.coupon_id)))

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

    # ── FUNC-008-02: 보유 쿠폰 보관함 ─────────────────────────────────────────

    def list_user_coupons(self, user_id: int, status: str | None = None) -> list[UserCoupon]:
        """사용자 보유 쿠폰 목록 조회. N+1 방지를 위해 coupon 관계를 joinedload."""
        stmt = (
            select(UserCoupon)
            .options(joinedload(UserCoupon.coupon))
            .where(UserCoupon.user_id == user_id)
            .order_by(UserCoupon.purchased_at.desc())
        )
        if status is not None:
            stmt = stmt.where(UserCoupon.status == status)
        return list(self.db.scalars(stmt))

    def get_user_coupon(self, user_coupon_id: int, user_id: int) -> UserCoupon | None:
        """사용자 보유 쿠폰 단건 조회 (소유자 검증 포함)."""
        stmt = (
            select(UserCoupon)
            .options(joinedload(UserCoupon.coupon))
            .where(UserCoupon.user_coupon_id == user_coupon_id, UserCoupon.user_id == user_id)
        )
        return self.db.scalar(stmt)
