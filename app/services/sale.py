from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import (
    SaleProductNotFoundError,
    SaleStoreNotFoundError,
    SubscriptionAlreadyExistsError,
    SubscriptionNotFoundError,
)
from app.models.sale import SaleProduct, SaleStore
from app.models.user import User
from app.repositories.sale import SaleRepository, SortOrder
from app.schemas.sale import (
    FeedResponse,
    SaleProductCard,
    SaleProductDetail,
    SaleStoreDetail,
    SaleStoreHourSchema,
    SaleStoreMarker,
    SubscribeResponse,
    _effective_status,
)


def _discount_rate(original: int, sale: int) -> float:
    if original == 0:
        return 0.0
    return round((original - sale) / original * 100, 1)


def _to_product_card(product: SaleProduct, store: SaleStore) -> SaleProductCard:
    return SaleProductCard(
        sale_product_id=product.sale_product_id,
        sale_store_id=product.sale_store_id,
        store_id=store.store_id,
        store_name=store.name,
        name=product.name,
        original_price=product.original_price,
        sale_price=product.sale_price,
        discount_rate=_discount_rate(product.original_price, product.sale_price),
        stock_quantity=product.stock_quantity,
        sale_deadline=product.sale_deadline,
        effective_status=_effective_status(
            product.status, product.stock_quantity, product.sale_deadline
        ),
        small_code=product.small_code,
        image_url=product.image_url,
    )


class SaleService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SaleRepository(db)

    # ── FUNC-004-01: 피드 ───────────────────────────────────────────────────

    def get_feed(
        self,
        *,
        small_code: str | None = None,
        sort: SortOrder = "deadline",
        q: str | None = None,
        user_lat: float | None = None,
        user_lon: float | None = None,
        page: int = 0,
        size: int = 20,
    ) -> FeedResponse:
        total = self.repo.count_feed(small_code=small_code, q=q)
        rows = self.repo.list_feed(
            small_code=small_code,
            sort=sort,
            q=q,
            user_lat=user_lat,
            user_lon=user_lon,
            page=page,
            size=size,
        )
        items = [_to_product_card(product, store) for product, store in rows]
        return FeedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            has_next=(page + 1) * size < total,
        )

    # ── FUNC-004-01: 관심 등록/해제 ─────────────────────────────────────────

    def subscribe(self, user: User, sale_store_id: int) -> SubscribeResponse:
        store = self.repo.get_store_by_id(sale_store_id)
        if store is None:
            raise SaleStoreNotFoundError()

        if self.repo.get_subscription(user.user_id, sale_store_id) is not None:
            raise SubscriptionAlreadyExistsError()

        self.repo.create_subscription(user.user_id, sale_store_id)
        self.db.commit()
        return SubscribeResponse(subscribed=True, sale_store_id=sale_store_id)

    def unsubscribe(self, user: User, sale_store_id: int) -> None:
        sub = self.repo.get_subscription(user.user_id, sale_store_id)
        if sub is None:
            raise SubscriptionNotFoundError()
        self.repo.delete_subscription(sub)
        self.db.commit()

    # ── FUNC-004-02: 지도 마커 ──────────────────────────────────────────────

    def get_store_markers(
        self,
        *,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        limit: int = 1000,
    ) -> list[SaleStoreMarker]:
        rows = self.repo.list_store_markers(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            limit=limit,
        )
        return [
            SaleStoreMarker(
                sale_store_id=store.sale_store_id,
                store_id=store.store_id,
                name=store.name,
                longitude=store.longitude,
                latitude=store.latitude,
                is_expiring_soon=is_expiring_soon,
            )
            for store, is_expiring_soon in rows
        ]

    # ── FUNC-004-03: 상점 상세 ──────────────────────────────────────────────

    def get_store_detail(self, sale_store_id: int) -> SaleStoreDetail:
        store = self.repo.get_store_detail(sale_store_id)
        if store is None:
            raise SaleStoreNotFoundError()

        # 활성 상품만 필터 (조회 시 실시간 보정)
        now = datetime.now(UTC)
        active_products = [
            p for p in store.products
            if p.sale_deadline > now and p.stock_quantity > 0
        ]

        return SaleStoreDetail(
            sale_store_id=store.sale_store_id,
            name=store.name,
            longitude=store.longitude,
            latitude=store.latitude,
            hours=[SaleStoreHourSchema.model_validate(h) for h in store.hours],
            products=[_to_product_card(p, store) for p in active_products],
        )

    # ── FUNC-004-03: 상품 상세 ──────────────────────────────────────────────

    def get_product_detail(self, sale_product_id: int) -> SaleProductDetail:
        row = self.repo.get_product(sale_product_id)
        if row is None:
            raise SaleProductNotFoundError()

        product, store = row
        return SaleProductDetail(
            sale_product_id=product.sale_product_id,
            sale_store_id=product.sale_store_id,
            store_id=store.store_id,
            store_name=store.name,
            name=product.name,
            original_price=product.original_price,
            sale_price=product.sale_price,
            discount_rate=_discount_rate(product.original_price, product.sale_price),
            stock_quantity=product.stock_quantity,
            sale_deadline=product.sale_deadline,
            effective_status=_effective_status(
                product.status, product.stock_quantity, product.sale_deadline
            ),
            small_code=product.small_code,
            image_url=product.image_url,
        )
