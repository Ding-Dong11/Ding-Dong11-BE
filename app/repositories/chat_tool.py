"""Claude Tool Use 에서 호출되는 실시간 DB 조회 레포지토리."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import exists, func, literal_column, select, text
from sqlalchemy.orm import Session

from app.models.disposition import AdminDisposition, DispositionType
from app.models.reward import RewardVerification, Store, StoreQrCode
from app.models.sale import SaleProduct, SaleStore


class ChatToolRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── 주변 상가 검색 ────────────────────────────────────────────────────────

    def nearby_stores(
        self,
        lat: float,
        lon: float,
        radius_km: float = 1.0,
        query: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """PostGIS ST_DWithin + tsvector 선택 검색으로 주변 상가 목록 반환."""
        radius_m = radius_km * 1000

        qr_exists = exists(
            select(StoreQrCode.qr_id)
            .where(StoreQrCode.store_id == Store.store_id)
            .where(StoreQrCode.is_active.is_(True))
        )
        disp_exists = exists(
            select(AdminDisposition.disposition_id)
            .where(AdminDisposition.store_id == Store.store_id)
        )
        sale_exists = exists(
            select(SaleProduct.sale_product_id)
            .join(SaleStore, SaleProduct.sale_store_id == SaleStore.sale_store_id)
            .where(SaleStore.store_id == Store.store_id)
            .where(SaleProduct.status == "ON_SALE")
        )

        stmt = select(
            Store.store_id,
            Store.store_name,
            Store.branch_name,
            Store.road_address,
            Store.jibun_address,
            Store.longitude,
            Store.latitude,
            literal_column(
                f"ST_Distance(stores.geom::geography,"
                f" ST_SetSRID(ST_MakePoint({float(lon)}, {float(lat)}), 4326)::geography)"
            ).label("dist_m"),
            qr_exists.label("has_active_qr"),
            disp_exists.label("has_disposition"),
            sale_exists.label("has_sale"),
        ).where(
            text(
                "stores.geom IS NOT NULL AND"
                " ST_DWithin(stores.geom::geography,"
                " ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)"
            )
        )

        if query:
            stmt = stmt.where(
                text("stores.search_tsv @@ websearch_to_tsquery('simple', :q)")
            )

        stmt = stmt.order_by(text("dist_m")).limit(limit)

        params: dict = {"lat": lat, "lon": lon, "radius_m": radius_m}
        if query:
            params["q"] = query

        rows = self.db.execute(stmt, params).mappings().all()
        return [
            {
                "store_id": r["store_id"],
                "store_name": r["store_name"],
                "branch_name": r["branch_name"],
                "address": r["road_address"] or r["jibun_address"] or "주소 미상",
                "distance_m": round(float(r["dist_m"] or 0)),
                "has_active_qr": bool(r["has_active_qr"]),
                "has_disposition": bool(r["has_disposition"]),
                "has_sale": bool(r["has_sale"]),
            }
            for r in rows
        ]

    # ── 상가 상세 ─────────────────────────────────────────────────────────────

    def store_detail(self, store_id: int) -> dict | None:
        """특정 상가 상세 정보 (행정처분 + 할인상품 포함)."""
        store = self.db.get(Store, store_id)
        if store is None:
            return None

        sale_rows = self.db.execute(
            select(
                SaleProduct.name,
                SaleProduct.original_price,
                SaleProduct.sale_price,
                SaleProduct.stock_quantity,
                SaleProduct.sale_deadline,
            )
            .join(SaleStore, SaleProduct.sale_store_id == SaleStore.sale_store_id)
            .where(SaleStore.store_id == store_id)
            .where(SaleProduct.status == "ON_SALE")
            .where(SaleProduct.stock_quantity > 0)
            .order_by(SaleProduct.sale_deadline)
        ).mappings().all()

        disp_rows = self.db.execute(
            select(
                DispositionType.type_name,
                AdminDisposition.disposition_date,
                AdminDisposition.violation_content,
                AdminDisposition.legal_basis,
            )
            .join(DispositionType, AdminDisposition.type_code == DispositionType.type_code)
            .where(AdminDisposition.store_id == store_id)
            .order_by(AdminDisposition.disposition_date.desc())
            .limit(5)
        ).mappings().all()

        def _discount(orig: int, sale: int) -> float:
            return round((orig - sale) / orig * 100, 1) if orig else 0.0

        return {
            "store_id": store.store_id,
            "store_name": store.store_name,
            "branch_name": store.branch_name,
            "address": store.road_address or store.jibun_address or "주소 미상",
            "has_active_qr": (self.db.scalar(
                select(func.count()).select_from(StoreQrCode).where(
                    StoreQrCode.store_id == store_id,
                    StoreQrCode.is_active.is_(True),
                )
            ) or 0) > 0,
            "sale_products": [
                {
                    "name": r["name"],
                    "original_price": r["original_price"],
                    "sale_price": r["sale_price"],
                    "discount_rate": _discount(r["original_price"], r["sale_price"]),
                    "stock": r["stock_quantity"],
                    "deadline": r["sale_deadline"].strftime("%m/%d %H:%M"),
                }
                for r in sale_rows
            ],
            "dispositions": [
                {
                    "type": r["type_name"],
                    "date": str(r["disposition_date"]),
                    "violation": r["violation_content"],
                    "legal_basis": r["legal_basis"],
                }
                for r in disp_rows
            ],
        }

    # ── 주변 할인 상품 ────────────────────────────────────────────────────────

    def nearby_sales(
        self,
        lat: float,
        lon: float,
        radius_km: float = 2.0,
        query: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """주변 마감할인 세일 상품 조회 (sale_stores longitude/latitude 기준)."""
        radius_m = radius_km * 1000
        now = datetime.now(timezone.utc)

        stmt = select(
            SaleProduct.name,
            SaleProduct.original_price,
            SaleProduct.sale_price,
            SaleProduct.stock_quantity,
            SaleProduct.sale_deadline,
            SaleStore.name.label("store_name"),
            literal_column(
                "ST_Distance("
                "  ST_SetSRID(ST_MakePoint(sale_stores.longitude::float,"
                "  sale_stores.latitude::float), 4326)::geography,"
                f"  ST_SetSRID(ST_MakePoint({float(lon)}, {float(lat)}), 4326)::geography"
                ")"
            ).label("dist_m"),
        ).join(
            SaleStore, SaleProduct.sale_store_id == SaleStore.sale_store_id
        ).where(
            SaleProduct.status == "ON_SALE",
            SaleProduct.stock_quantity > 0,
            SaleProduct.sale_deadline > now,
            text(
                "ST_DWithin("
                "  ST_SetSRID(ST_MakePoint(sale_stores.longitude::float,"
                "   sale_stores.latitude::float), 4326)::geography,"
                "  ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,"
                "  :radius_m"
                ")"
            ),
        )

        if query:
            stmt = stmt.where(
                text("sale_products.search_tsv @@ websearch_to_tsquery('simple', :q)")
            )

        stmt = stmt.order_by(text("dist_m"), SaleProduct.sale_deadline).limit(limit)

        params: dict = {"lat": lat, "lon": lon, "radius_m": radius_m}
        if query:
            params["q"] = query

        rows = self.db.execute(stmt, params).mappings().all()

        def _discount(orig: int, sale: int) -> float:
            return round((orig - sale) / orig * 100, 1) if orig else 0.0

        return [
            {
                "product_name": r["name"],
                "store_name": r["store_name"],
                "original_price": r["original_price"],
                "sale_price": r["sale_price"],
                "discount_rate": _discount(r["original_price"], r["sale_price"]),
                "stock": r["stock_quantity"],
                "deadline": r["sale_deadline"].strftime("%m/%d %H:%M"),
                "distance_m": round(float(r["dist_m"] or 0)),
            }
            for r in rows
        ]

    # ── 행정처분 검색 ─────────────────────────────────────────────────────────

    def search_dispositions(
        self,
        query: str,
        lat: float | None = None,
        lon: float | None = None,
        radius_km: float = 3.0,
        limit: int = 10,
    ) -> list[dict]:
        """상호명/업종 키워드 + 선택적 위치 반경으로 행정처분 이력 검색."""
        stmt = (
            select(
                AdminDisposition.business_name,
                DispositionType.type_name,
                AdminDisposition.disposition_date,
                AdminDisposition.violation_content,
                AdminDisposition.legal_basis,
                AdminDisposition.longitude,
                AdminDisposition.latitude,
            )
            .join(DispositionType, AdminDisposition.type_code == DispositionType.type_code)
            .where(
                text("admin_dispositions.search_tsv @@ websearch_to_tsquery('simple', :q)")
            )
        )

        params: dict = {"q": query}

        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
            params["radius_m"] = radius_km * 1000
            stmt = stmt.where(
                text(
                    "admin_dispositions.geom IS NOT NULL AND"
                    " ST_DWithin(admin_dispositions.geom::geography,"
                    " ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)"
                )
            )

        stmt = stmt.order_by(AdminDisposition.disposition_date.desc()).limit(limit)

        rows = self.db.execute(stmt, params).mappings().all()
        return [
            {
                "business_name": r["business_name"],
                "type": r["type_name"],
                "date": str(r["disposition_date"]),
                "violation": r["violation_content"] or "내용 없음",
                "legal_basis": r["legal_basis"] or "",
            }
            for r in rows
        ]

    # ── 개인 맞춤 추천 ────────────────────────────────────────────────────────

    def my_recommendations(
        self,
        user_id: int,
        lat: float,
        lon: float,
        radius_km: float = 2.0,
        limit: int = 10,
    ) -> list[dict]:
        """QR 인증 이력 기반 맞춤 추천 — 동일 업종 미방문 상가 (반경 내, 방문자 오름차순)."""
        radius_m = radius_km * 1000

        # 사용자가 인증한 업종 코드
        small_codes = list(
            self.db.scalars(
                select(Store.small_code)
                .join(RewardVerification, RewardVerification.store_id == Store.store_id)
                .where(RewardVerification.user_id == user_id)
                .where(Store.small_code.isnot(None))
                .distinct()
            )
        )

        if not small_codes:
            return self.nearby_stores(lat, lon, radius_km, limit=limit)

        visited_ids = list(
            self.db.scalars(
                select(RewardVerification.store_id)
                .where(RewardVerification.user_id == user_id)
                .distinct()
            )
        )

        visit_count = func.count(RewardVerification.reward_verification_id).label("visit_count")

        conditions = [
            Store.small_code.in_(small_codes),
            text(
                "stores.geom IS NOT NULL AND"
                " ST_DWithin(stores.geom::geography,"
                " ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)"
            ),
        ]
        if visited_ids:
            conditions.append(Store.store_id.notin_(visited_ids))

        stmt = (
            select(
                Store.store_id,
                Store.store_name,
                Store.road_address,
                Store.jibun_address,
                literal_column(
                    f"ST_Distance(stores.geom::geography,"
                    f" ST_SetSRID(ST_MakePoint({float(lon)}, {float(lat)}), 4326)::geography)"
                ).label("dist_m"),
                visit_count,
            )
            .outerjoin(RewardVerification, RewardVerification.store_id == Store.store_id)
            .where(*conditions)
            .group_by(Store.store_id)
            .order_by(visit_count.asc(), text("dist_m"))
            .limit(limit)
        )

        rows = self.db.execute(stmt, {"lat": lat, "lon": lon, "radius_m": radius_m}).mappings().all()
        return [
            {
                "store_id": r["store_id"],
                "store_name": r["store_name"],
                "address": r["road_address"] or r["jibun_address"] or "주소 미상",
                "distance_m": round(float(r["dist_m"] or 0)),
                "visitor_count": int(r["visit_count"]),
                "reason": "방문하신 상가와 같은 업종 중 아직 방문하지 않은 상가입니다.",
            }
            for r in rows
        ]
