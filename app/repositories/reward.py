from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.reward import PointTransaction, RewardVerification, StoreQrCode


class RewardRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── QR ──────────────────────────────────────────────────────────────────

    def get_active_qr_by_token(self, qr_token: str) -> StoreQrCode | None:
        """활성 QR 토큰으로 QR 코드 조회 (store eager load)."""
        stmt = select(StoreQrCode).where(
            StoreQrCode.qr_token == qr_token, StoreQrCode.is_active.is_(True)
        )
        return self.db.scalar(stmt)

    def get_active_qr_by_store(self, store_id: int) -> StoreQrCode | None:
        """상가의 현재 활성 QR 조회."""
        stmt = select(StoreQrCode).where(
            StoreQrCode.store_id == store_id, StoreQrCode.is_active.is_(True)
        )
        return self.db.scalar(stmt)

    def deactivate_qr(self, qr: StoreQrCode) -> None:
        """QR 비활성화."""
        qr.is_active = False

    def create_qr(self, *, store_id: int, qr_token: str, reward_point: int) -> StoreQrCode:
        """새 QR 코드 생성."""
        qr = StoreQrCode(store_id=store_id, qr_token=qr_token, reward_point=reward_point)
        self.db.add(qr)
        self.db.flush()
        return qr

    # ── 인증 이력 ────────────────────────────────────────────────────────────

    def has_verified_today(self, user_id: int, store_id: int) -> bool:
        """오늘(UTC) 동일 상가를 이미 인증했는지 확인."""
        today = datetime.now(UTC).date()
        stmt = select(RewardVerification.reward_verification_id).where(
            RewardVerification.user_id == user_id,
            RewardVerification.store_id == store_id,
            func.date(RewardVerification.verified_at) == today,
        )
        return self.db.scalar(stmt) is not None

    def create_verification(
        self,
        *,
        user_id: int,
        store_id: int,
        qr_id: int,
        awarded_point: int,
    ) -> RewardVerification:
        verification = RewardVerification(
            user_id=user_id,
            store_id=store_id,
            qr_id=qr_id,
            awarded_point=awarded_point,
        )
        self.db.add(verification)
        self.db.flush()
        return verification

    # ── 포인트 원장 ──────────────────────────────────────────────────────────

    def create_point_transaction(
        self,
        *,
        user_id: int,
        amount: int,
        tx_type: str,
        balance_after: int,
        reward_verification_id: int | None = None,
        user_coupon_id: int | None = None,
    ) -> PointTransaction:
        tx = PointTransaction(
            user_id=user_id,
            amount=amount,
            tx_type=tx_type,
            balance_after=balance_after,
            reward_verification_id=reward_verification_id,
            user_coupon_id=user_coupon_id,
        )
        self.db.add(tx)
        return tx
