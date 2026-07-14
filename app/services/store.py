from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import StoreNotFoundError
from app.repositories.store import StoreRepository
from app.schemas.store import MarkerItem, StoreDetail

_CLUSTER_ZOOM_THRESHOLD = 14  # 이 줌 미만이면 클러스터링, 이상이면 개별 마커


def _cluster_eps(zoom: int) -> float:
    """줌 레벨 → ST_ClusterDBSCAN eps (EPSG:4326 도 단위).

    zoom  8 → ~0.035° (~3.9 km)
    zoom 10 → ~0.009° (~1.0 km)
    zoom 12 → ~0.002° (~240 m)
    zoom 13 → ~0.001° (~120 m)
    """
    return max(0.0009, 1_000_000.0 / (2 ** zoom * 111_000))


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
        if zoom < _CLUSTER_ZOOM_THRESHOLD:
            return self.repo.list_markers_clustered(
                min_lat=min_lat,
                max_lat=max_lat,
                min_lon=min_lon,
                max_lon=max_lon,
                eps_deg=_cluster_eps(zoom),
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
