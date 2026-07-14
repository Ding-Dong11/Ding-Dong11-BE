from __future__ import annotations

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.models.disposition import AdminDisposition, DispositionType
from app.models.reward import Store, StoreQrCode
from app.models.sale import SaleProduct, SaleStore
from app.schemas.store import DispositionSummary, SaleProductSummary, StoreDetail, StoreMarker

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
