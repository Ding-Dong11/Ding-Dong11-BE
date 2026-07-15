from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, computed_field


# ── 마커 유니온 ──────────────────────────────────────────────────────────────

class AreaMarker(BaseModel):
    """카카오맵 level 8+ 광역 뷰에서 서버가 ST_SnapToGrid 로 집계해 반환하는 영역 핀.

    격자 셀 하나에 포함된 상가 수(count)와 해당 셀 중심 좌표를 제공한다.
    클라이언트는 CustomOverlay 로 count 숫자 뱃지를 렌더링하고,
    탭 시 map.setLevel(현재레벨 - 2) + panTo 로 줌인한다.
    """

    type: Literal["area"] = "area"
    longitude: float
    latitude: float
    count: int
    has_active_qr: bool     # 셀 내 QR 상가 1개 이상 존재
    has_disposition: bool   # 셀 내 행정처분 상가 존재
    has_sale: bool          # 셀 내 할인 상품 상가 존재


class StoreMarker(BaseModel):
    """카카오맵 level 1–7 상세 뷰에서 반환하는 개별 상가 핀.

    클라이언트는 Kakao MarkerClusterer 에 이 마커들을 그대로 넘겨
    시각적 클러스터링을 위임한다.
    """

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
    Union[AreaMarker, StoreMarker],
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

class StoreSearchResult(BaseModel):
    """GET /stores/search — 상가명·주소 전문검색 결과 한 건."""

    store_id: int
    store_name: str
    branch_name: str | None
    road_address: str | None
    longitude: float
    latitude: float
    has_active_qr: bool
    has_disposition: bool
    has_sale: bool


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
