from __future__ import annotations

from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.reward import QrVerifyRequest, QrVerifyResponse
from app.services.reward import RewardService

router = APIRouter(prefix="/rewards", tags=["rewards"])


def get_reward_service(
    db: Session = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> RewardService:
    return RewardService(db=db, redis=redis)


@router.post("/verify", response_model=QrVerifyResponse)
def verify_qr(
    body: QrVerifyRequest,
    current_user: User = Depends(get_current_user),
    service: RewardService = Depends(get_reward_service),
) -> QrVerifyResponse:
    """FUNC-003-03: QR 토큰 인증 후 포인트 적립.

    - QR 토큰이 유효하지 않으면 404.
    - 오늘 이미 인증한 상가면 409.
    - 성공 시 포인트 적립 및 잔액 반환.
    """
    return service.verify_qr(current_user, body.qr_token)
