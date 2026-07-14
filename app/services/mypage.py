from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import UserCouponNotFoundError
from app.models.user import User
from app.repositories.coupon import CouponRepository
from app.schemas.mypage import PointResponse, UserCouponDetail, UserCouponItem


class MyPageService:
    def __init__(self, db: Session):
        self.db = db
        self.coupon_repo = CouponRepository(db)

    # ── FUNC-008-01: 보유 포인트 조회 ────────────────────────────────────────────

    def get_point(self, user: User) -> PointResponse:
        return PointResponse(user_id=user.user_id, point_balance=user.point_balance)

    # ── FUNC-008-02: 보유 쿠폰 보관함 ───────────────────────────────────────────

    def list_my_coupons(self, user: User, status: str | None = None) -> list[UserCouponItem]:
        user_coupons = self.coupon_repo.list_user_coupons(user.user_id, status=status)
        return [UserCouponItem.from_orm_with_coupon(uc) for uc in user_coupons]

    def get_my_coupon_detail(self, user: User, user_coupon_id: int) -> UserCouponDetail:
        uc = self.coupon_repo.get_user_coupon(user_coupon_id, user.user_id)
        if uc is None:
            raise UserCouponNotFoundError()
        return UserCouponDetail.from_orm_with_coupon(uc)
