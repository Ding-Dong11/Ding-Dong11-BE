from __future__ import annotations

from pydantic import BaseModel, Field


class QrIssueRequest(BaseModel):
    """QR 발급 요청."""

    reward_point: int = Field(gt=0, description="인증 시 지급할 포인트")


class QrIssueResponse(BaseModel):
    """QR 발급 응답."""

    qr_id: int
    store_id: int
    store_name: str
    qr_token: str
    qr_url: str
    reward_point: int
    is_active: bool
