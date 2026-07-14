from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/dispositions", tags=["dispositions"])
# 행정처분 마커·상세는 GET /stores/markers, GET /stores/{id} 로 통합됨
