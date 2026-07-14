from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, computed_field


# ── 마커 (클러스터 / 개별 상가 유니온) ──────────────────────────────────────

class ClusterMarker(BaseModel):
    """zoom < 14 구간에서 서버가 묶어 반환하는 클러스터 핀."""

    type: Literal["cluster"] = "cluster"
    longitude: float
    latitude: float
    count: int              # 클러스터 내 상가 수
    has_active_qr: bool     # 클러스터 내 1개 이상 QR 상가 존재
    has_disposition: bool   # 클러스터 내 행정처분 상가 존재
    has_sale: bool          # 클러스터 내 할인 상품 상가 존재


class StoreMarker(BaseModel):
    """GET /stores/markers — 개별 상가 핀 한 건 (zoom >= 14 또는 클러스터 크기 1)."""

    type: Literal["store"] = "store"
    store_id: int
    store_name: str
    longitude: float
    latitude: float
    has_active_qr: bool     # [포인트 지급] 뱃지
    has_disposition: bool   # 행정처분 이력 → 마커 색상 구분
    has_sale: bool          # 활성 할인 상품 존재


# FastAPI response_model 에 사용할 discriminated union
MarkerItem = Annotated[
    Union[ClusterMarker, StoreMarker],
    Field(discriminator="type"),
]


# ── 상세 서브 스키마 ─────────────────────────────────────────────────────────

class SaleProductSummary(BaseModel):
    """마커 팝업 내 할인 상품 카드."""

    sale_product_id: int
    name: str
    original_price: int
    sale_price: int
    image_url: str | None
    effective_status: str   # ON_SALE / SOLD_OUT / EXPIRED

    @computed_field
    @property
    def discount_rate(self) -> float:
        if self.original_price == 0:
            return 0.0
        return round((self.original_price - self.sale_price) / self.original_price * 100, 1)


class DispositionSummary(BaseModel):
    """마커 팝업 내 행정처분 이력 한 건."""

    disposition_id: int
    type_name: str
    disposition_date: date
    violation_content: str | None
    legal_basis: str | None


# ── 통합 상세 ────────────────────────────────────────────────────────────────

class StoreDetail(BaseModel):
    """GET /stores/{store_id} — 마커 클릭 팝업 전체 정보."""

    store_id: int
    store_name: str
    branch_name: str | None
    road_address: str | None
    jibun_address: str | None
    longitude: Decimal
    latitude: Decimal
    image_url: str | None
    has_active_qr: bool
    sale_products: list[SaleProductSummary]     # 활성 할인 상품 (없으면 빈 리스트)
    dispositions: list[DispositionSummary]      # 행정처분 이력 (없으면 빈 리스트)
