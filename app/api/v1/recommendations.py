from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_recommendation_service(db: Session = Depends(get_session)) -> RecommendationService:
    return RecommendationService(db=db)


@router.get("", response_model=RecommendationResponse)
def get_recommendations(
    lat: Annotated[float, Query(description="현재 위치 위도")],
    lon: Annotated[float, Query(description="현재 위치 경도")],
    radius_km: Annotated[float, Query(ge=0.1, le=20.0, description="추천 반경 (km)")] = 2.0,
    limit: Annotated[int, Query(ge=1, le=100, description="최대 추천 건수")] = 20,
    current_user: User = Depends(get_current_user),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    """FUNC-006-01: 오늘의 추천 상점 목록.

    사용자의 QR 인증 이력에서 가장 많이 이용한 업종(small_code)을 추출하고,
    현재 위치 반경 내 해당 카테고리 상점을 랜덤으로 추천한다.
    이력이 없으면 위치 기반 전체 랜덤 추천으로 폴백한다.
    """
    return service.get_recommendations(
        current_user.user_id,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        limit=limit,
    )
