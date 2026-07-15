from __future__ import annotations

from redis import Redis
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AlreadyVerifiedTodayError,
    QrNotFoundError,
)
from app.core.redis_keys import store_cooldown_key
from app.models.user import User
from app.repositories.reward import RewardRepository
from app.schemas.reward import QrVerifyResponse

_COOLDOWN_SECONDS = 7 * 24 * 3600  # 7일


class RewardService:
    def __init__(self, db: Session, redis: Redis):
        self.db = db
        self.redis = redis
        self.reward_repo = RewardRepository(db)

    def verify_qr(self, user: User, qr_token: str) -> QrVerifyResponse:
        """QR 토큰 검증 후 포인트 적립. 원장·잔액·인증이력을 동일 트랜잭션으로 원자 갱신."""
        qr = self.reward_repo.get_active_qr_by_token(qr_token)
        if qr is None:
            raise QrNotFoundError()

        store = qr.store

        if self.redis.exists(store_cooldown_key(user.user_id, store.store_id)):
            raise AlreadyVerifiedTodayError()

        new_balance = user.point_balance + qr.reward_point
        verification = self.reward_repo.create_verification(
            user_id=user.user_id,
            store_id=store.store_id,
            qr_id=qr.qr_id,
            awarded_point=qr.reward_point,
        )
        self.reward_repo.create_point_transaction(
            user_id=user.user_id,
            amount=qr.reward_point,
            tx_type="REWARD_EARN",
            balance_after=new_balance,
            reward_verification_id=verification.reward_verification_id,
        )
        user.point_balance = new_balance
        self.db.commit()

        self.redis.setex(store_cooldown_key(user.user_id, store.store_id), _COOLDOWN_SECONDS, "1")

        return QrVerifyResponse(
            store_id=store.store_id,
            store_name=store.store_name,
            awarded_point=qr.reward_point,
            balance_after=new_balance,
        )
