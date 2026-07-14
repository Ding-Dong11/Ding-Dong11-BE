from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class StoreMarker(BaseModel):
    """FUNC-003-01: 지도 마커 한 건."""

    store_id: int
    store_name: str
    branch_name: str | None
    longitude: Decimal
    latitude: Decimal
    small_code: str | None

    model_config = {"from_attributes": True}


class StoreDetail(BaseModel):
    """FUNC-003-01: 마커 클릭 시 상세 팝업."""

    store_id: int
    store_name: str
    branch_name: str | None
    small_code: str | None
    road_address: str | None
    jibun_address: str | None
    longitude: Decimal
    latitude: Decimal

    model_config = {"from_attributes": True}


class QrVerifyRequest(BaseModel):
    """FUNC-003-03: QR 인증 요청."""

    qr_token: str = Field(min_length=1)


class QrVerifyResponse(BaseModel):
    """FUNC-003-03: QR 인증 응답."""

    store_id: int
    store_name: str
    awarded_point: int
    balance_after: int


class PointBalanceResponse(BaseModel):
    """현재 사용자 포인트 잔액."""

    user_id: int
    point_balance: int
