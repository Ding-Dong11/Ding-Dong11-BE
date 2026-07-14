from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.reward import PointTransaction, RewardVerification, Store, StoreQrCode


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

    # ── 추천 컨텍스트 조회 ──────────────────────────────────────────────────

    def get_user_verified_store_ids(self, user_id: int) -> list[int]:
        """사용자가 QR 인증한 상가 ID 목록 (중복 제거)."""
        stmt = (
            select(RewardVerification.store_id)
            .where(RewardVerification.user_id == user_id)
            .distinct()
        )
        return list(self.db.scalars(stmt))

    def get_user_verified_small_codes(self, user_id: int) -> list[str]:
        """사용자가 인증한 상가들의 업종 소분류 코드 (distinct)."""
        stmt = (
            select(Store.small_code)
            .join(RewardVerification, RewardVerification.store_id == Store.store_id)
            .where(
                RewardVerification.user_id == user_id,
                Store.small_code.isnot(None),
            )
            .distinct()
        )
        return list(self.db.scalars(stmt))

    def list_similar_stores_ranked(
        self,
        small_codes: list[str],
        exclude_store_ids: list[int],
        limit: int = 10,
    ) -> list[tuple[Store, int]]:
        """같은 업종 상가를 수요 알고리즘(방문자 수 오름차순)으로 정렬.

        방문자(reward_verifications)가 적을수록 상단에 표시 — 덜 알려진 상가 우선.
        """
        visit_count_col = func.count(RewardVerification.reward_verification_id)
        conditions = [Store.small_code.in_(small_codes)]
        if exclude_store_ids:
            conditions.append(Store.store_id.notin_(exclude_store_ids))

        stmt = (
            select(Store, visit_count_col.label("visit_count"))
            .outerjoin(RewardVerification, RewardVerification.store_id == Store.store_id)
            .where(*conditions)
            .group_by(Store.store_id)
            .order_by(visit_count_col.asc())
            .limit(limit)
        )
        return [(row[0], row[1]) for row in self.db.execute(stmt)]

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
