from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from app.models.sale import SaleProduct, SaleStore, SaleStoreHour, SaleSubscription

_EXPIRING_SOON_HOURS = 2  # 마감 임박 기준 (시간)
_MARKER_LIMIT_MAX = 2000

SortOrder = str  # "deadline" | "discount" | "distance"


class SaleRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── FUNC-004-01: 피드 ───────────────────────────────────────────────────

    def count_feed(
        self,
        *,
        small_code: str | None,
        q: str | None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(SaleProduct)
            .where(
                SaleProduct.status == "ON_SALE",
                SaleProduct.sale_deadline > func.now(),
                SaleProduct.stock_quantity > 0,
            )
        )
        if small_code:
            stmt = stmt.where(SaleProduct.small_code == small_code)
        if q:
            stmt = stmt.where(
                text(
                    "sale_products.search_tsv @@ websearch_to_tsquery('simple', :q)"
                ).bindparams(q=q)
            )
        return self.db.scalar(stmt) or 0

    def list_feed(
        self,
        *,
        small_code: str | None = None,
        sort: SortOrder = "deadline",
        q: str | None = None,
        user_lat: float | None = None,
        user_lon: float | None = None,
        page: int = 0,
        size: int = 20,
    ) -> list[tuple[SaleProduct, SaleStore]]:
        """세일 피드 — ON_SALE + 재고 있음 + 마감 전 상품. FUNC-004-01."""
        stmt = (
            select(SaleProduct, SaleStore)
            .join(SaleStore, SaleStore.sale_store_id == SaleProduct.sale_store_id)
            .where(
                SaleProduct.status == "ON_SALE",
                SaleProduct.sale_deadline > func.now(),
                SaleProduct.stock_quantity > 0,
            )
        )
        if small_code:
            stmt = stmt.where(SaleProduct.small_code == small_code)
        if q:
            stmt = stmt.where(
                text(
                    "sale_products.search_tsv @@ websearch_to_tsquery('simple', :q)"
                ).bindparams(q=q)
            )

        if sort == "discount":
            stmt = stmt.order_by(
                ((SaleProduct.original_price - SaleProduct.sale_price)
                 * 1.0 / SaleProduct.original_price).desc()
            )
        elif sort == "distance" and user_lat is not None and user_lon is not None:
            stmt = stmt.order_by(
                text(
                    "ST_Distance(sale_stores.geom::geography, "
                    "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) ASC"
                ).bindparams(lon=user_lon, lat=user_lat)
            )
        else:
            # 기본: 마감 임박순
            stmt = stmt.order_by(SaleProduct.sale_deadline.asc())

        stmt = stmt.offset(page * size).limit(size)
        return list(self.db.execute(stmt))

    # ── FUNC-004-01: 관심 등록 ──────────────────────────────────────────────

    def get_subscription(self, user_id: int, sale_store_id: int) -> SaleSubscription | None:
        stmt = select(SaleSubscription).where(
            SaleSubscription.user_id == user_id,
            SaleSubscription.sale_store_id == sale_store_id,
        )
        return self.db.scalar(stmt)

    def create_subscription(self, user_id: int, sale_store_id: int) -> SaleSubscription:
        sub = SaleSubscription(user_id=user_id, sale_store_id=sale_store_id)
        self.db.add(sub)
        self.db.flush()
        return sub

    def delete_subscription(self, sub: SaleSubscription) -> None:
        self.db.delete(sub)

    # ── FUNC-004-02: 지도 마커 ──────────────────────────────────────────────

    def list_store_markers(
        self,
        *,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        limit: int = 1000,
    ) -> list[tuple[SaleStore, bool]]:
        """세일 상점 마커 목록. 마감 임박 여부(is_expiring_soon) 포함. FUNC-004-02."""
        soon = datetime.now(UTC) + timedelta(hours=_EXPIRING_SOON_HOURS)

        stmt = select(SaleStore)
        if min_lat is not None:
            stmt = stmt.where(SaleStore.latitude >= min_lat)
        if max_lat is not None:
            stmt = stmt.where(SaleStore.latitude <= max_lat)
        if min_lon is not None:
            stmt = stmt.where(SaleStore.longitude >= min_lon)
        if max_lon is not None:
            stmt = stmt.where(SaleStore.longitude <= max_lon)
        stmt = stmt.order_by(SaleStore.sale_store_id).limit(min(limit, _MARKER_LIMIT_MAX))

        stores = list(self.db.scalars(stmt))

        # 마감 임박 상점 ID 집합
        soon_ids_stmt = select(SaleProduct.sale_store_id).where(
            SaleProduct.status == "ON_SALE",
            SaleProduct.sale_deadline > func.now(),
            SaleProduct.sale_deadline <= soon,
        ).distinct()
        soon_store_ids: set[int] = set(self.db.scalars(soon_ids_stmt))

        return [(store, store.sale_store_id in soon_store_ids) for store in stores]

    # ── FUNC-004-03: 상점 상세 ──────────────────────────────────────────────

    def get_store_detail(self, sale_store_id: int) -> SaleStore | None:
        """영업시간과 활성 상품 목록을 포함한 상점 상세. FUNC-004-03."""
        stmt = (
            select(SaleStore)
            .options(
                selectinload(SaleStore.hours),
                selectinload(SaleStore.products),
            )
            .where(SaleStore.sale_store_id == sale_store_id)
        )
        return self.db.scalar(stmt)

    # ── FUNC-004-03: 상품 상세 ──────────────────────────────────────────────

    def get_product(self, sale_product_id: int) -> tuple[SaleProduct, SaleStore] | None:
        stmt = (
            select(SaleProduct, SaleStore)
            .join(SaleStore, SaleStore.sale_store_id == SaleProduct.sale_store_id)
            .where(SaleProduct.sale_product_id == sale_product_id)
        )
        row = self.db.execute(stmt).first()
        return row  # type: ignore[return-value]

    def get_store_by_id(self, sale_store_id: int) -> SaleStore | None:
        return self.db.get(SaleStore, sale_store_id)
