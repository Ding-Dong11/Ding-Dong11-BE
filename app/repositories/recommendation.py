from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.reward import RewardVerification, Store

_LIMIT_MAX = 100


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_top_small_code(self, user_id: int) -> str | None:
        """사용자 QR 인증 이력에서 가장 많이 이용한 small_code 반환. 이력 없으면 None."""
        stmt = (
            select(Store.small_code)
            .join(RewardVerification, RewardVerification.store_id == Store.store_id)
            .where(
                RewardVerification.user_id == user_id,
                Store.small_code.is_not(None),
            )
            .group_by(Store.small_code)
            .order_by(func.count().desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list_recommendations(
        self,
        *,
        lat: float,
        lon: float,
        radius_km: float,
        small_code: str | None,
        limit: int,
    ) -> list[Store]:
        """반경 내 상점을 랜덤 추출. small_code 있으면 해당 카테고리 우선, 부족하면 전체로 보충.

        PostGIS ST_DWithin + GiST 인덱스 활용 (database.md 공간 쿼리 컨벤션).
        """
        capped = min(limit, _LIMIT_MAX)

        # stores.geom 은 DB Generated (Numeric → geometry(Point,4326)) 컬럼 — GiST 인덱스 사용
        within_clause = text(
            "ST_DWithin("
            "  stores.geom::geography,"
            "  ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,"
            "  :radius_m"
            ")"
        ).bindparams(lon=lon, lat=lat, radius_m=radius_km * 1000)

        base = select(Store).where(within_clause)

        if small_code:
            category_stmt = (
                base.where(Store.small_code == small_code)
                .order_by(func.random())
                .limit(capped)
            )
            results = list(self.db.scalars(category_stmt))
            if len(results) >= capped:
                return results

            # 카테고리 결과가 부족하면 다른 카테고리로 보충
            already_ids = {s.store_id for s in results}
            remaining = capped - len(results)
            if already_ids:
                fallback_stmt = (
                    base.where(Store.store_id.not_in(already_ids))
                    .order_by(func.random())
                    .limit(remaining)
                )
            else:
                fallback_stmt = base.order_by(func.random()).limit(remaining)
            results += list(self.db.scalars(fallback_stmt))
            return results

        return list(self.db.scalars(base.order_by(func.random()).limit(capped)))
