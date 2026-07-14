from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import StoreNotFoundError
from app.repositories.store import StoreRepository
from app.schemas.store import StoreDetail, StoreMarker


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
        limit: int,
    ) -> list[StoreMarker]:
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
