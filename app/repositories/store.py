from __future__ import annotations

from sqlalchemy import exists, func, select, text
from sqlalchemy.orm import Session

from app.models.disposition import AdminDisposition, DispositionType
from app.models.reward import Store, StoreQrCode
from app.models.sale import SaleProduct, SaleStore
from app.schemas.store import (
    AreaMarker,
    DispositionSummary,
    MarkerItem,
    SaleProductSummary,
    StoreDetail,
    StoreMarker,
    StoreSearchResult,
)

_MARKER_LIMIT_MAX = 2000


def _qr_exists(store_id_col):
    return exists(
        select(StoreQrCode.qr_id)
        .where(StoreQrCode.store_id == store_id_col)
        .where(StoreQrCode.is_active.is_(True))
    )


def _disposition_exists(store_id_col):
    return exists(
        select(AdminDisposition.disposition_id)
        .where(AdminDisposition.store_id == store_id_col)
    )


def _sale_exists(store_id_col):
    return exists(
        select(SaleProduct.sale_product_id)
        .join(SaleStore, SaleProduct.sale_store_id == SaleStore.sale_store_id)
        .where(SaleStore.store_id == store_id_col)
        .where(SaleProduct.status == "ON_SALE")
    )


class StoreRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_markers(
        self,
        *,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        limit: int = 1000,
    ) -> list[StoreMarker]:
        """bbox 내 상가 마커 목록 — FUNC-003-01."""
        stmt = select(
            Store.store_id,
            Store.store_name,
            Store.longitude,
            Store.latitude,
            _qr_exists(Store.store_id).label("has_active_qr"),
            _disposition_exists(Store.store_id).label("has_disposition"),
            _sale_exists(Store.store_id).label("has_sale"),
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
        rows = self.db.execute(stmt.order_by(Store.store_id).limit(capped)).mappings().all()
        return [StoreMarker(**row) for row in rows]

    def list_markers_area(
        self,
        *,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        grid_deg: float,
        limit: int = 500,
    ) -> list[AreaMarker]:
        """ST_SnapToGrid 로 격자 집계 → 카카오맵 level 8+ 광역 뷰용.

        각 격자 셀의 중심 좌표(ST_X/Y of snapped geom)와 상가 수를 반환.
        geom 이 NULL 인 상가는 자동 제외된다.
        """
        sql = text("""
            WITH flagged AS (
                SELECT
                    s.geom,
                    EXISTS(
                        SELECT 1 FROM store_qr_codes q
                        WHERE q.store_id = s.store_id AND q.is_active
                    ) AS has_active_qr,
                    EXISTS(
                        SELECT 1 FROM admin_dispositions d
                        WHERE d.store_id = s.store_id
                    ) AS has_disposition,
                    EXISTS(
                        SELECT 1 FROM sale_products sp
                        JOIN sale_stores ss ON sp.sale_store_id = ss.sale_store_id
                        WHERE ss.store_id = s.store_id AND sp.status = 'ON_SALE'
                    ) AS has_sale
                FROM stores s
                WHERE s.geom IS NOT NULL
                  AND (:min_lat IS NULL OR s.latitude >= :min_lat)
                  AND (:max_lat IS NULL OR s.latitude <= :max_lat)
                  AND (:min_lon IS NULL OR s.longitude >= :min_lon)
                  AND (:max_lon IS NULL OR s.longitude <= :max_lon)
            ),
            snapped AS (
                SELECT
                    ST_SnapToGrid(geom, :grid_deg) AS cell,
                    has_active_qr,
                    has_disposition,
                    has_sale
                FROM flagged
            )
            SELECT
                ST_X(cell)::float   AS longitude,
                ST_Y(cell)::float   AS latitude,
                COUNT(*)::int       AS count,
                BOOL_OR(has_active_qr)   AS has_active_qr,
                BOOL_OR(has_disposition) AS has_disposition,
                BOOL_OR(has_sale)        AS has_sale
            FROM snapped
            GROUP BY cell
            LIMIT :limit
        """)

        rows = self.db.execute(sql, {
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon,
            "grid_deg": grid_deg,
            "limit": limit,
        }).mappings().all()

        return [
            AreaMarker(
                longitude=r["longitude"],
                latitude=r["latitude"],
                count=r["count"],
                has_active_qr=r["has_active_qr"],
                has_disposition=r["has_disposition"],
                has_sale=r["has_sale"],
            )
            for r in rows
        ]

    def search_stores(self, q: str, limit: int = 20) -> list[StoreSearchResult]:
        """상가명·지점명·도로명주소 tsvector 전문검색 — GET /stores/search."""
        stmt = (
            select(
                Store.store_id,
                Store.store_name,
                Store.branch_name,
                Store.road_address,
                Store.longitude,
                Store.latitude,
                _qr_exists(Store.store_id).label("has_active_qr"),
                _disposition_exists(Store.store_id).label("has_disposition"),
                _sale_exists(Store.store_id).label("has_sale"),
            )
            .where(text("stores.search_tsv @@ plainto_tsquery('simple', :q)"))
            .order_by(text("ts_rank(stores.search_tsv, plainto_tsquery('simple', :q)) DESC"))
            .limit(limit)
        )
        rows = self.db.execute(stmt, {"q": q}).mappings().all()
        return [StoreSearchResult(**row) for row in rows]

    def get_by_id(self, store_id: int) -> Store | None:
        return self.db.get(Store, store_id)

    def get_detail(self, store_id: int) -> StoreDetail | None:
        """마커 팝업 상세 — FUNC-003-02 팝업."""
        store = self.db.get(Store, store_id)
        if store is None:
            return None

        has_active_qr = bool(
            self.db.scalar(
                select(func.count()).select_from(StoreQrCode).where(
                    StoreQrCode.store_id == store_id,
                    StoreQrCode.is_active.is_(True),
                )
            )
        )

        sale_rows = self.db.execute(
            select(
                SaleProduct.sale_product_id,
                SaleProduct.name,
                SaleProduct.original_price,
                SaleProduct.sale_price,
                SaleProduct.image_url,
                SaleProduct.status.label("effective_status"),
            )
            .join(SaleStore, SaleProduct.sale_store_id == SaleStore.sale_store_id)
            .where(SaleStore.store_id == store_id)
            .where(SaleProduct.status == "ON_SALE")
            .order_by(SaleProduct.sale_product_id)
        ).mappings().all()

        disp_rows = self.db.execute(
            select(
                AdminDisposition.disposition_id,
                DispositionType.type_name,
                AdminDisposition.disposition_date,
                AdminDisposition.violation_content,
                AdminDisposition.legal_basis,
            )
            .join(DispositionType, AdminDisposition.type_code == DispositionType.type_code)
            .where(AdminDisposition.store_id == store_id)
            .order_by(AdminDisposition.disposition_date.desc())
        ).mappings().all()

        return StoreDetail(
            store_id=store.store_id,
            store_name=store.store_name,
            branch_name=store.branch_name,
            road_address=store.road_address,
            jibun_address=store.jibun_address,
            longitude=store.longitude,
            latitude=store.latitude,
            image_url=store.image_url,
            has_active_qr=has_active_qr,
            sale_products=[SaleProductSummary(**r) for r in sale_rows],
            dispositions=[DispositionSummary(**r) for r in disp_rows],
        )
