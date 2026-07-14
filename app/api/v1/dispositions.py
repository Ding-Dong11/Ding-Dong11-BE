from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.disposition import DispositionDetail, DispositionMarker, DispositionTypeSchema
from app.services.disposition import DispositionService

router = APIRouter(prefix="/dispositions", tags=["dispositions"])


def get_disposition_service(db: Session = Depends(get_session)) -> DispositionService:
    return DispositionService(db=db)


@router.get("/markers", response_model=list[DispositionMarker])
def get_markers(
    type_code: Annotated[str | None, Query(description="처분 유형 코드 필터")] = None,
    small_code: Annotated[str | None, Query(description="업종 소분류 코드 필터")] = None,
    q: Annotated[str | None, Query(description="업체명 키워드 검색")] = None,
    min_lat: Annotated[float | None, Query(description="뷰포트 최소 위도")] = None,
    max_lat: Annotated[float | None, Query(description="뷰포트 최대 위도")] = None,
    min_lon: Annotated[float | None, Query(description="뷰포트 최소 경도")] = None,
    max_lon: Annotated[float | None, Query(description="뷰포트 최대 경도")] = None,
    limit: Annotated[int, Query(ge=1, le=2000, description="최대 반환 건수")] = 1000,
    service: DispositionService = Depends(get_disposition_service),
) -> list[DispositionMarker]:
    """FUNC-002-01/03/04: 행정처분 지도 마커 목록.

    좌표(longitude/latitude)가 있는 건만 반환한다.
    클러스터링(FUNC-002-03)은 클라이언트에서 처리한다.
    """
    items = service.get_markers(
        type_code=type_code,
        small_code=small_code,
        q=q,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        limit=limit,
    )
    return [DispositionMarker.model_validate(item) for item in items]


@router.get("/types", response_model=list[DispositionTypeSchema])
def list_types(
    service: DispositionService = Depends(get_disposition_service),
) -> list[DispositionTypeSchema]:
    """FUNC-002-04: 처분 유형 전체 목록 (필터 드롭다운용)."""
    return [DispositionTypeSchema.model_validate(t) for t in service.list_types()]


@router.get("/{disposition_id}", response_model=DispositionDetail)
def get_detail(
    disposition_id: int,
    service: DispositionService = Depends(get_disposition_service),
) -> DispositionDetail:
    """FUNC-002-02: 마커 클릭 시 팝업 상세 정보."""
    return DispositionDetail.model_validate(service.get_detail(disposition_id))
