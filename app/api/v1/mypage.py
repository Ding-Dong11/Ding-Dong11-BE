from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.mypage import PointResponse, UserCouponDetail, UserCouponItem
from app.services.mypage import MyPageService

router = APIRouter(prefix="/mypage", tags=["mypage"])


def get_mypage_service(db: Session = Depends(get_session)) -> MyPageService:
    return MyPageService(db=db)


# ── FUNC-008-01: 보유 포인트 조회 ──────────────────────────────────────────────

@router.get("/point", response_model=PointResponse)
def get_point(
    current_user: User = Depends(get_current_user),
    service: MyPageService = Depends(get_mypage_service),
) -> PointResponse:
    """FUNC-008-01: 현재 사용자의 보유 포인트 조회."""
    return service.get_point(current_user)


# ── FUNC-008-02: 보유 쿠폰 보관함 ─────────────────────────────────────────────

@router.get("/coupons", response_model=list[UserCouponItem])
def list_my_coupons(
    status: Annotated[
        str | None,
        Query(description="쿠폰 상태 필터 (UNUSED / USED / EXPIRED)"),
    ] = None,
    current_user: User = Depends(get_current_user),
    service: MyPageService = Depends(get_mypage_service),
) -> list[UserCouponItem]:
    """FUNC-008-02: 보유 쿠폰 보관함 목록.

    status 파라미터로 UNUSED / USED / EXPIRED 필터링 가능.
    생략 시 전체 반환.
    """
    return service.list_my_coupons(current_user, status=status)


@router.get("/coupons/{user_coupon_id}", response_model=UserCouponDetail)
def get_my_coupon_detail(
    user_coupon_id: int,
    current_user: User = Depends(get_current_user),
    service: MyPageService = Depends(get_mypage_service),
) -> UserCouponDetail:
    """FUNC-008-02: 보유 쿠폰 상세 조회 (이미지·사용기간·바코드 포함).

    다른 사용자의 쿠폰이거나 존재하지 않으면 404.
    """
    return service.get_my_coupon_detail(current_user, user_coupon_id)
