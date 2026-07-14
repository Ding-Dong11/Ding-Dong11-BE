from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DispositionTypeSchema(BaseModel):
    type_code: str
    type_name: str

    model_config = {"from_attributes": True}


class DispositionMarker(BaseModel):
    """FUNC-002-01: 지도 마커 한 건 (좌표 보장 — longitude/latitude NOT NULL)."""

    disposition_id: int
    longitude: Decimal
    latitude: Decimal
    business_name: str
    type_code: str

    model_config = {"from_attributes": True}


class DispositionDetail(BaseModel):
    """FUNC-002-02: 마커 클릭 시 팝업 상세."""

    disposition_id: int
    business_name: str
    disposition_type: DispositionTypeSchema | None
    disposition_date: date
    violation_content: str | None
    legal_basis: str | None
    authority: str | None
    small_code: str | None
    adong_code: str | None
    longitude: Decimal | None
    latitude: Decimal | None

    model_config = {"from_attributes": True}
