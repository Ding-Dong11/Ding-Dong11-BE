from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import StoreNotFoundError, StoreQrNotFoundError
from app.repositories.reward import RewardRepository
from app.repositories.store import StoreRepository
from app.schemas.admin import QrIssueResponse

_QR_SCHEME = "dingdong://verify?token={token}"


def _build_qr_url(qr_token: str) -> str:
    return _QR_SCHEME.format(token=qr_token)


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.store_repo = StoreRepository(db)
        self.reward_repo = RewardRepository(db)

    def issue_qr(self, store_id: int, reward_point: int) -> QrIssueResponse:
        """상가에 QR 발급. 기존 활성 QR이 있으면 비활성화 후 새로 발급."""
        store = self.store_repo.get_by_id(store_id)
        if store is None:
            raise StoreNotFoundError()

        existing = self.reward_repo.get_active_qr_by_store(store_id)
        if existing is not None:
            self.reward_repo.deactivate_qr(existing)

        qr_token = str(uuid.uuid4())
        qr = self.reward_repo.create_qr(
            store_id=store_id,
            qr_token=qr_token,
            reward_point=reward_point,
        )
        self.db.commit()

        return QrIssueResponse(
            qr_id=qr.qr_id,
            store_id=store.store_id,
            store_name=store.store_name,
            qr_token=qr_token,
            qr_url=_build_qr_url(qr_token),
            reward_point=reward_point,
            is_active=True,
        )

    def get_store_qr(self, store_id: int) -> QrIssueResponse:
        """상가의 현재 활성 QR 조회."""
        store = self.store_repo.get_by_id(store_id)
        if store is None:
            raise StoreNotFoundError()

        qr = self.reward_repo.get_active_qr_by_store(store_id)
        if qr is None:
            raise StoreQrNotFoundError()

        return QrIssueResponse(
            qr_id=qr.qr_id,
            store_id=store.store_id,
            store_name=store.store_name,
            qr_token=qr.qr_token,
            qr_url=_build_qr_url(qr.qr_token),
            reward_point=qr.reward_point,
            is_active=qr.is_active,
        )
