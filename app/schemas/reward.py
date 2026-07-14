from __future__ import annotations

from pydantic import BaseModel, Field


class QrVerifyRequest(BaseModel):
    """FUNC-003-03: QR 인증 요청."""

    qr_token: str = Field(min_length=1)


class QrVerifyResponse(BaseModel):
    """FUNC-003-03: QR 인증 응답."""

    store_id: int
    store_name: str
    awarded_point: int
    balance_after: int
