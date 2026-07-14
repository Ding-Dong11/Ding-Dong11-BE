from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import DispositionNotFoundError
from app.models.disposition import AdminDisposition, DispositionType
from app.repositories.disposition import DispositionRepository


class DispositionService:
    def __init__(self, db: Session):
        self.db = db
        self._repo = DispositionRepository(db)

    def get_markers(
        self,
        *,
        type_code: str | None = None,
        small_code: str | None = None,
        q: str | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        limit: int = 1000,
    ) -> list[AdminDisposition]:
        return self._repo.list_markers(
            type_code=type_code,
            small_code=small_code,
            q=q,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            limit=limit,
        )

    def get_detail(self, disposition_id: int) -> AdminDisposition:
        d = self._repo.get_by_id(disposition_id)
        if d is None:
            raise DispositionNotFoundError()
        return d

    def list_types(self) -> list[DispositionType]:
        return self._repo.list_types()
