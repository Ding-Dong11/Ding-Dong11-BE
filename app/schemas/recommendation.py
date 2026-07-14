from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class RecommendationItem(BaseModel):
    """FUNC-006-01: 추천 상점 한 건."""

    store_id: int
    store_name: str
    branch_name: str | None
    road_address: str | None
    jibun_address: str | None
    longitude: Decimal
    latitude: Decimal
    small_code: str | None

    model_config = {"from_attributes": True}


class RecommendationResponse(BaseModel):
    """FUNC-006-01: 오늘의 추천 상점 목록."""

    date: date
    top_small_code: str | None
    items: list[RecommendationItem]

    model_config = {"from_attributes": True}
