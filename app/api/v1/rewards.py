from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.reward import (
    QrVerifyRequest,
    QrVerifyResponse,
    StoreDetail,
    StoreMarker,
)
from app.services.reward import RewardService

router = APIRouter(prefix="/rewards", tags=["rewards"])


def get_reward_service(db: Session = Depends(get_session)) -> RewardService:
    return RewardService(db=db)


# ── FUNC-003-01: 상가 지도 마커 / 상세 ────────────────────────────────────────

@router.get("/stores/markers", response_model=list[StoreMarker])
def get_store_markers(
    small_code: Annotated[str | None, Query(description="업종 소분류 코드 필터")] = None,
    q: Annotated[str | None, Query(description="상가명 키워드 검색")] = None,
    min_lat: Annotated[float | None, Query(description="뷰포트 최소 위도")] = None,
    max_lat: Annotated[float | None, Query(description="뷰포트 최대 위도")] = None,
    min_lon: Annotated[float | None, Query(description="뷰포트 최소 경도")] = None,
    max_lon: Annotated[float | None, Query(description="뷰포트 최대 경도")] = None,
    limit: Annotated[int, Query(ge=1, le=2000, description="최대 반환 건수")] = 1000,
    service: RewardService = Depends(get_reward_service),
) -> list[StoreMarker]:
    """FUNC-003-01: 상가 지도 마커 목록.

    클러스터링은 클라이언트에서 처리한다 (FUNC-003-01 UI/UX).
    """
    return service.get_store_markers(
        small_code=small_code,
        q=q,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        limit=limit,
    )


@router.get("/stores/{store_id}", response_model=StoreDetail)
def get_store_detail(
    store_id: int,
    service: RewardService = Depends(get_reward_service),
) -> StoreDetail:
    """FUNC-003-01: 상가 상세 정보 (마커 클릭 팝업용)."""
    return service.get_store_detail(store_id)


# ── FUNC-003-03: QR 인증 + 포인트 적립 ─────────────────────────────────────────

@router.post("/verify", response_model=QrVerifyResponse)
def verify_qr(
    body: QrVerifyRequest,
    current_user: User = Depends(get_current_user),
    service: RewardService = Depends(get_reward_service),
) -> QrVerifyResponse:
    """FUNC-003-03: QR 토큰 인증 후 포인트 적립.

    - QR 토큰이 유효하지 않으면 404.
    - 오늘 이미 인증한 상가면 409.
    - 성공 시 포인트 적립 및 잔액 반환.
    """
    return service.verify_qr(current_user, body.qr_token)
