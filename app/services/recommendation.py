from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.repositories.recommendation import RecommendationRepository
from app.schemas.recommendation import RecommendationItem, RecommendationResponse


class RecommendationService:
    def __init__(self, db: Session):
        self.repo = RecommendationRepository(db)

    def get_recommendations(
        self,
        user_id: int,
        *,
        lat: float,
        lon: float,
        radius_km: float = 2.0,
        limit: int = 20,
    ) -> RecommendationResponse:
        top_code = self.repo.get_top_small_code(user_id)
        stores = self.repo.list_recommendations(
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            small_code=top_code,
            limit=limit,
        )
        return RecommendationResponse(
            date=date.today(),
            top_small_code=top_code,
            items=[RecommendationItem.model_validate(s) for s in stores],
        )
