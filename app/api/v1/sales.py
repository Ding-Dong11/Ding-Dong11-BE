from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.sale import (
    FeedResponse,
    SaleProductDetail,
    SaleStoreMarker,
    SubscribeResponse,
)
from app.services.sale import SaleService

router = APIRouter(prefix="/sales", tags=["sales"])


def get_sale_service(db: Session = Depends(get_session)) -> SaleService:
    return SaleService(db=db)


# ── FUNC-004-01: 세일 피드 ──────────────────────────────────────────────────

@router.get("/feed", response_model=FeedResponse)
def get_feed(
    small_code: Annotated[str | None, Query(description="업종 소분류 코드 필터")] = None,
    sort: Annotated[
        Literal["deadline", "discount", "distance"],
        Query(description="정렬 기준: deadline(마감 임박순) | discount(할인율 높은순) | distance(거리순)"),
    ] = "deadline",
    q: Annotated[str | None, Query(description="상품명 키워드 검색")] = None,
    user_lat: Annotated[float | None, Query(description="사용자 위도 (distance 정렬 시 필요)")] = None,
    user_lon: Annotated[float | None, Query(description="사용자 경도 (distance 정렬 시 필요)")] = None,
    page: Annotated[int, Query(ge=0, description="페이지 번호 (0-indexed)")] = 0,
    size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 20,
    service: SaleService = Depends(get_sale_service),
) -> FeedResponse:
    """FUNC-004-01: 세일 상품 피드.

    ON_SALE 상태 + 재고 있음 + 마감 전 상품만 반환한다.
    할인율(discount_rate)은 (원가-할인가)/원가 * 100으로 계산된다.
    distance 정렬 시 user_lat, user_lon 이 필요하다.
    """
    return service.get_feed(
        small_code=small_code,
        sort=sort,
        q=q,
        user_lat=user_lat,
        user_lon=user_lon,
        page=page,
        size=size,
    )


# ── FUNC-004-01: 관심 등록/해제 ─────────────────────────────────────────────

@router.post("/stores/{sale_store_id}/subscribe", response_model=SubscribeResponse, status_code=201)
def subscribe(
    sale_store_id: int,
    current_user: User = Depends(get_current_user),
    service: SaleService = Depends(get_sale_service),
) -> SubscribeResponse:
    """FUNC-004-01: 세일 상점 관심 등록."""
    return service.subscribe(current_user, sale_store_id)


@router.delete("/stores/{sale_store_id}/subscribe", status_code=204)
def unsubscribe(
    sale_store_id: int,
    current_user: User = Depends(get_current_user),
    service: SaleService = Depends(get_sale_service),
) -> None:
    """FUNC-004-01: 세일 상점 관심 해제."""
    service.unsubscribe(current_user, sale_store_id)


# ── FUNC-004-02: 지도 마커 ──────────────────────────────────────────────────

@router.get("/stores/markers", response_model=list[SaleStoreMarker])
def get_store_markers(
    min_lat: Annotated[float | None, Query(description="뷰포트 최소 위도")] = None,
    max_lat: Annotated[float | None, Query(description="뷰포트 최대 위도")] = None,
    min_lon: Annotated[float | None, Query(description="뷰포트 최소 경도")] = None,
    max_lon: Annotated[float | None, Query(description="뷰포트 최대 경도")] = None,
    limit: Annotated[int, Query(ge=1, le=2000, description="최대 반환 건수")] = 1000,
    service: SaleService = Depends(get_sale_service),
) -> list[SaleStoreMarker]:
    """FUNC-004-02: 세일 상점 지도 마커.

    is_expiring_soon=true 인 상점은 FE에서 마커 색상을 다르게 표시한다.
    마감 임박 기준: ON_SALE 상품 중 2시간 이내 마감.
    """
    return service.get_store_markers(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        limit=limit,
    )


# ── FUNC-004-03: 상품 상세 ─────────────────────────────────────────────────

@router.get("/products/{sale_product_id}", response_model=SaleProductDetail)
def get_product_detail(
    sale_product_id: int,
    service: SaleService = Depends(get_sale_service),
) -> SaleProductDetail:
    """FUNC-004-03: 세일 상품 상세.

    재고(stock_quantity)와 effective_status 를 매 요청마다 실시간으로 반환한다.
    FE는 sale_deadline 과 현재 시각의 차이로 카운트다운 타이머를 계산한다.
    """
    return service.get_product_detail(sale_product_id)
