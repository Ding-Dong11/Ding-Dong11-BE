from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import CouponInactiveError, CouponNotFoundError, InsufficientPointError
from app.models.reward import PointTransaction
from app.models.user import User
from app.repositories.coupon import CouponRepository
from app.schemas.coupon import CouponDetail, CouponItem, CouponPurchaseResponse


class CouponService:
    def __init__(self, db: Session):
        self.db = db
        self.coupon_repo = CouponRepository(db)

    # ── FUNC-007-02: 구매 가능 쿠폰 목록 ────────────────────────────────────────

    def list_coupons(
        self,
        *,
        q: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
    ) -> list[CouponItem]:
        coupons = self.coupon_repo.list_active(q=q, min_price=min_price, max_price=max_price)
        return [CouponItem.model_validate(c) for c in coupons]

    def get_coupon_detail(self, coupon_id: int) -> CouponDetail:
        coupon = self.coupon_repo.get_by_id(coupon_id)
        if coupon is None:
            raise CouponNotFoundError()
        if not coupon.is_active:
            raise CouponInactiveError()
        return CouponDetail.model_validate(coupon)

    # ── FUNC-007-01: 포인트로 쿠폰 구매 ─────────────────────────────────────────

    def purchase_coupon(self, user: User, coupon_id: int) -> CouponPurchaseResponse:
        """포인트로 쿠폰 구매. 포인트 차감·원장·UserCoupon 생성을 동일 트랜잭션으로 원자 처리."""
        coupon = self.coupon_repo.get_by_id(coupon_id)
        if coupon is None:
            raise CouponNotFoundError()
        if not coupon.is_active:
            raise CouponInactiveError()
        if user.point_balance < coupon.point_price:
            raise InsufficientPointError()

        new_balance = user.point_balance - coupon.point_price
        barcode = uuid.uuid4().hex
        valid_until = datetime.now(UTC) + timedelta(days=90)

        user_coupon = self.coupon_repo.create_user_coupon(
            user_id=user.user_id,
            coupon_id=coupon.coupon_id,
            barcode=barcode,
            valid_until=valid_until,
        )

        tx = PointTransaction(
            user_id=user.user_id,
            amount=-coupon.point_price,
            tx_type="COUPON_REDEEM",
            balance_after=new_balance,
            user_coupon_id=user_coupon.user_coupon_id,
        )
        self.db.add(tx)

        user.point_balance = new_balance
        self.db.commit()
        self.db.refresh(user_coupon)

        return CouponPurchaseResponse(
            user_coupon_id=user_coupon.user_coupon_id,
            coupon_id=coupon.coupon_id,
            name=coupon.name,
            barcode=user_coupon.barcode,
            status=user_coupon.status,
            purchased_at=user_coupon.purchased_at,
            valid_until=user_coupon.valid_until,
            balance_after=new_balance,
        )
