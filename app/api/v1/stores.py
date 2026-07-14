from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.store import StoreDetail, StoreMarker
from app.services.store import StoreService

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/markers", response_model=list[StoreMarker])
def get_store_markers(
    min_lat: Annotated[float | None, Query(description="bbox 최소 위도")] = None,
    max_lat: Annotated[float | None, Query(description="bbox 최대 위도")] = None,
    min_lon: Annotated[float | None, Query(description="bbox 최소 경도")] = None,
    max_lon: Annotated[float | None, Query(description="bbox 최대 경도")] = None,
    limit: Annotated[int, Query(ge=1, le=2000)] = 1000,
    db: Session = Depends(get_session),
):
    """지도 뷰포트 내 상가 마커 목록 (FUNC-003-01).

    - `has_active_qr`: 포인트 적립 가능 상가 여부 (뱃지 표시용)
    - `has_disposition`: 행정처분 이력 존재 여부 (마커 색상 구분용)
    - `has_sale`: 현재 ON_SALE 할인 상품 존재 여부
    """
    return StoreService(db).list_markers(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        limit=limit,
    )


@router.get("/{store_id}", response_model=StoreDetail)
def get_store_detail(
    store_id: int,
    db: Session = Depends(get_session),
):
    """상가 마커 클릭 팝업 상세 (FUNC-003-02).

    - `sale_products`: 활성(ON_SALE) 할인 상품만 포함 (없으면 빈 리스트)
    - `dispositions`: 연결된 행정처분 이력 (없으면 빈 리스트)
    """
    return StoreService(db).get_detail(store_id)
