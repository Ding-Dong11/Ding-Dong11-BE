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
    zoom: Annotated[int, Query(ge=1, le=20, description="현재 지도 줌 레벨 (1–20)")],
    min_lat: Annotated[float | None, Query(description="bbox 최소 위도")] = None,
    max_lat: Annotated[float | None, Query(description="bbox 최대 위도")] = None,
    min_lon: Annotated[float | None, Query(description="bbox 최소 경도")] = None,
    max_lon: Annotated[float | None, Query(description="bbox 최대 경도")] = None,
    limit: Annotated[int, Query(ge=1, le=2000)] = 1000,
    db: Session = Depends(get_session),
):
    """지도 뷰포트 내 상가 마커 목록 (FUNC-003-01).

    zoom < 14 : 서버사이드 클러스터링 결과 반환
      - type="cluster" : 클러스터 핀 (count, 중심 좌표, 통합 플래그)
      - type="store"   : 클러스터 크기 1 (단독 상가)

    zoom >= 14 : 개별 상가 마커 (bbox + limit 적용)
      - type="store"   : 상가 핀

    공통 플래그:
      - has_active_qr  : 포인트 적립 가능 (뱃지 표시용)
      - has_disposition: 행정처분 이력 존재 (마커 색상 구분용)
      - has_sale       : 현재 할인 상품 존재
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

    type="store" 마커 클릭 시 호출. 클러스터 마커 클릭엔 사용 불가.
    """
    return StoreService(db).get_detail(store_id)
