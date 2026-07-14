from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import StoreNotFoundError
from app.repositories.store import StoreRepository
from app.schemas.store import MarkerItem, StoreDetail

# 카카오맵 level 8 이상이면 광역 격자 집계, 7 이하면 개별 마커
_AREA_ZOOM_THRESHOLD = 8


def _area_grid_deg(zoom: int) -> float:
    """카카오맵 레벨 → ST_SnapToGrid 격자 크기 (EPSG:4326 도 단위).

    뷰포트 너비 ≈ 0.5 * 2^level km, 격자 크기 = 뷰포트 / 8 (약 8×8 그리드).

    level  8 → ~0.144° (~16km 격자)
    level 10 → ~0.577° (~64km 격자)
    level 12 → ~2.306° (~256km 격자)
    level 14 → 3.0° 상한 적용
    """
    return min(3.0, max(0.08, (2 ** zoom) / 1776.0))


class StoreService:
    def __init__(self, db: Session):
        self.repo = StoreRepository(db)

    def list_markers(
        self,
        *,
        min_lat: float | None,
        max_lat: float | None,
        min_lon: float | None,
        max_lon: float | None,
        zoom: int,
        limit: int,
    ) -> list[MarkerItem]:
        """카카오맵 레벨에 따라 두 가지 응답을 반환한다.

        level 1–7 (동네 수준): 개별 StoreMarker 목록
          → 클라이언트가 Kakao MarkerClusterer 에 위임해 시각적 클러스터링

        level 8–14 (도시·광역): AreaMarker 격자 집계 목록
          → 클라이언트가 CustomOverlay 로 count 숫자 뱃지 렌더링
        """
        if zoom >= _AREA_ZOOM_THRESHOLD:
            return self.repo.list_markers_area(
                min_lat=min_lat,
                max_lat=max_lat,
                min_lon=min_lon,
                max_lon=max_lon,
                grid_deg=_area_grid_deg(zoom),
                limit=limit,
            )
        return self.repo.list_markers(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            limit=limit,
        )

    def get_detail(self, store_id: int) -> StoreDetail:
        detail = self.repo.get_detail(store_id)
        if detail is None:
            raise StoreNotFoundError()
        return detail
