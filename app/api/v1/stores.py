from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.store import MarkerItem, StoreDetail
from app.services.store import StoreService

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/markers", response_model=list[MarkerItem])
def get_store_markers(
    zoom: Annotated[int, Query(ge=1, le=14, description="카카오맵 레벨 (1=가장 가까이, 14=가장 멀리)")],
    min_lat: Annotated[float | None, Query(description="bbox 최소 위도")] = None,
    max_lat: Annotated[float | None, Query(description="bbox 최대 위도")] = None,
    min_lon: Annotated[float | None, Query(description="bbox 최소 경도")] = None,
    max_lon: Annotated[float | None, Query(description="bbox 최대 경도")] = None,
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
    db: Session = Depends(get_session),
):
    """지도 뷰포트 내 상가 마커 목록 (FUNC-003-01) — 카카오맵 하이브리드 2티어.

    level 1–7 (동네 수준) → type="store" 개별 마커 목록
      클라이언트가 Kakao MarkerClusterer 에 전달해 시각적 클러스터링.
      limit 파라미터 적용 (기본 500).

    level 8–14 (도시·광역) → type="area" 격자 집계 목록
      ST_SnapToGrid 로 격자 셀별 상가 수 집계.
      클라이언트가 CustomOverlay 로 count 숫자 뱃지 렌더링,
      탭 시 map.setLevel(현재레벨 - 2) + panTo 줌인.

    공통 플래그:
      has_active_qr   : 포인트 적립 가능
      has_disposition : 행정처분 이력 존재
      has_sale        : 현재 할인 상품 존재
    """
    return StoreService(db).list_markers(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        zoom=zoom,
        limit=limit,
    )


@router.get("/{store_id}", response_model=StoreDetail)
def get_store_detail(
    store_id: int,
    db: Session = Depends(get_session),
):
    """상가 마커 클릭 팝업 상세 (FUNC-003-02).

    type="store" 마커 클릭 시에만 호출. type="area" 탭엔 줌인 동작만 수행.
    """
    return StoreService(db).get_detail(store_id)
