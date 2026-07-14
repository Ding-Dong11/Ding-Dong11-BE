from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models.disposition import AdminDisposition, DispositionType

_MARKER_LIMIT_MAX = 2000


class DispositionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_markers(
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
        """좌표가 있는 처분 건 목록. FUNC-002-01/03/04."""
        stmt = select(AdminDisposition).where(
            AdminDisposition.longitude.is_not(None),
            AdminDisposition.latitude.is_not(None),
        )
        if type_code:
            stmt = stmt.where(AdminDisposition.type_code == type_code)
        if small_code:
            stmt = stmt.where(AdminDisposition.small_code == small_code)
        if q:
            # search_tsv 는 generated 컬럼 — GIN 인덱스 활용 (develop.md)
            stmt = stmt.where(
                text("admin_dispositions.search_tsv @@ websearch_to_tsquery('simple', :q)").bindparams(q=q)
            )
        if min_lat is not None:
            stmt = stmt.where(AdminDisposition.latitude >= min_lat)
        if max_lat is not None:
            stmt = stmt.where(AdminDisposition.latitude <= max_lat)
        if min_lon is not None:
            stmt = stmt.where(AdminDisposition.longitude >= min_lon)
        if max_lon is not None:
            stmt = stmt.where(AdminDisposition.longitude <= max_lon)

        capped = min(limit, _MARKER_LIMIT_MAX)
        stmt = stmt.order_by(AdminDisposition.disposition_date.desc()).limit(capped)
        return list(self.db.scalars(stmt))

    def get_by_id(self, disposition_id: int) -> AdminDisposition | None:
        """단건 상세 — disposition_type 관계 함께 로드. FUNC-002-02."""
        stmt = (
            select(AdminDisposition)
            .options(selectinload(AdminDisposition.disposition_type))
            .where(AdminDisposition.disposition_id == disposition_id)
        )
        return self.db.scalar(stmt)

    def list_types(self) -> list[DispositionType]:
        """처분 유형 전체 목록 — 필터 드롭다운용. FUNC-002-04."""
        stmt = select(DispositionType).order_by(DispositionType.type_name)
        return list(self.db.scalars(stmt))
