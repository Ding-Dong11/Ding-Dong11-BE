from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.admin import QrIssueRequest, QrIssueResponse
from app.services.admin import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_service(db: Session = Depends(get_session)) -> AdminService:
    return AdminService(db=db)


@router.post("/stores/{store_id}/qr", response_model=QrIssueResponse, status_code=201)
def issue_qr(
    store_id: int,
    body: QrIssueRequest,
    service: AdminService = Depends(get_admin_service),
) -> QrIssueResponse:
    """상가에 QR 코드 발급.

    기존 활성 QR이 있으면 비활성화 후 새 QR을 발급한다.
    응답의 qr_url 값을 QR 이미지로 인코딩해 상가에 부착한다.
    형식: dingdong://verify?token=<UUID v4>
    """
    return service.issue_qr(store_id, body.reward_point)


@router.get("/stores/{store_id}/qr", response_model=QrIssueResponse)
def get_store_qr(
    store_id: int,
    service: AdminService = Depends(get_admin_service),
) -> QrIssueResponse:
    """상가의 현재 활성 QR 조회."""
    return service.get_store_qr(store_id)
