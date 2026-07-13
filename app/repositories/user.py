from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_active_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.status == "ACTIVE")
        return self.db.scalars(stmt).first()

    def create(self, email: str, password_hash: str) -> User:
        user = User(email=email, password_hash=password_hash)
        self.db.add(user)
        self.db.flush()
        return user

    def withdraw(self, user: User) -> None:
        user.status = "WITHDRAWN"
        user.withdrawn_at = datetime.now(UTC)
