from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AlreadyVerifiedTodayError,
    QrNotFoundError,
    StoreNotFoundError,
)
from app.models.user import User
from app.repositories.reward import RewardRepository
from app.repositories.store import StoreRepository
from app.schemas.reward import QrVerifyResponse, StoreDetail, StoreMarker


class RewardService:
    def __init__(self, db: Session):
        self.db = db
        self.store_repo = StoreRepository(db)
        self.reward_repo = RewardRepository(db)

    # ── FUNC-003-01: 상가 지도 마커 / 상세 ───────────────────────────────────

    def get_store_markers(
        self,
        *,
        small_code: str | None = None,
        q: str | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        limit: int = 1000,
    ) -> list[StoreMarker]:
        stores = self.store_repo.list_markers(
            small_code=small_code,
            q=q,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            limit=limit,
        )
        return [StoreMarker.model_validate(s) for s in stores]

    def get_store_detail(self, store_id: int) -> StoreDetail:
        store = self.store_repo.get_by_id(store_id)
        if store is None:
            raise StoreNotFoundError()
        return StoreDetail.model_validate(store)

    # ── FUNC-003-03: QR 인증 + 포인트 적립 ──────────────────────────────────

    def verify_qr(self, user: User, qr_token: str) -> QrVerifyResponse:
        """QR 토큰 검증 후 포인트 적립. 원장·잔액·인증이력을 동일 트랜잭션으로 원자 갱신."""
        qr = self.reward_repo.get_active_qr_by_token(qr_token)
        if qr is None:
            raise QrNotFoundError()

        store = qr.store

        if self.reward_repo.has_verified_today(user.user_id, store.store_id):
            raise AlreadyVerifiedTodayError()

        # 원자 트랜잭션: 인증이력 생성 → 포인트 원장 기록 → 잔액 갱신 (database.md 트랜잭션 원칙)
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

        return QrVerifyResponse(
            store_id=store.store_id,
            store_name=store.store_name,
            awarded_point=qr.reward_point,
            balance_after=new_balance,
        )
