from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.coupon import CouponDetail, CouponItem, CouponPurchaseResponse
from app.services.coupon import CouponService

router = APIRouter(prefix="/coupons", tags=["coupons"])


def get_coupon_service(db: Session = Depends(get_session)) -> CouponService:
    return CouponService(db=db)


# ── FUNC-007-02: 구매 가능 쿠폰 목록 ───────────────────────────────────────────

@router.get("", response_model=list[CouponItem])
def list_coupons(
    service: CouponService = Depends(get_coupon_service),
) -> list[CouponItem]:
    """FUNC-007-02: 구매 가능한 쿠폰 목록 조회.

    is_active=true 인 쿠폰만 반환한다.
    """
    return service.list_coupons()


@router.get("/{coupon_id}", response_model=CouponDetail)
def get_coupon_detail(
    coupon_id: int,
    service: CouponService = Depends(get_coupon_service),
) -> CouponDetail:
    """FUNC-007-01: 쿠폰 상세 조회 (클릭 후 구매 전 확인 화면)."""
    return service.get_coupon_detail(coupon_id)


# ── FUNC-007-01: 포인트로 쿠폰 구매 ────────────────────────────────────────────

@router.post("/{coupon_id}/purchase", response_model=CouponPurchaseResponse, status_code=201)
def purchase_coupon(
    coupon_id: int,
    current_user: User = Depends(get_current_user),
    service: CouponService = Depends(get_coupon_service),
) -> CouponPurchaseResponse:
    """FUNC-007-01: 포인트로 쿠폰 구매.

    - 포인트 잔액이 부족하면 400.
    - 비활성 쿠폰이면 400.
    - 성공 시 바코드와 변경된 포인트 잔액 반환.
    """
    return service.purchase_coupon(current_user, coupon_id)
