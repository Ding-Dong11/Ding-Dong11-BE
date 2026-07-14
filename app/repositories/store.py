from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.reward import Store

_MARKER_LIMIT_MAX = 2000


class StoreRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_markers(
        self,
        *,
        small_code: str | None = None,
        q: str | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        limit: int = 1000,
    ) -> list[Store]:
        """좌표가 있는 상가 목록. FUNC-003-01."""
        stmt = select(Store)
        if small_code:
            stmt = stmt.where(Store.small_code == small_code)
        if q:
            stmt = stmt.where(
                text("stores.search_tsv @@ websearch_to_tsquery('simple', :q)").bindparams(q=q)
            )
        if min_lat is not None:
            stmt = stmt.where(Store.latitude >= min_lat)
        if max_lat is not None:
            stmt = stmt.where(Store.latitude <= max_lat)
        if min_lon is not None:
            stmt = stmt.where(Store.longitude >= min_lon)
        if max_lon is not None:
            stmt = stmt.where(Store.longitude <= max_lon)

        capped = min(limit, _MARKER_LIMIT_MAX)
        return list(self.db.scalars(stmt.order_by(Store.store_id).limit(capped)))

    def get_by_id(self, store_id: int) -> Store | None:
        return self.db.get(Store, store_id)
