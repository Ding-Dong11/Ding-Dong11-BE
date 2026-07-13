from __future__ import annotations

from datetime import UTC, datetime

from redis import Redis
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import Settings
from app.core.exceptions import (
    DuplicateEmailError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidVerificationCodeError,
    PasswordMismatchError,
    TokenInvalidError,
    UserWithdrawnError,
    VerificationCooldownError,
)
from app.core.mailer import send_verification_email
from app.core.redis_keys import (
    access_blacklist_key,
    email_code_key,
    email_cooldown_key,
    email_verified_key,
    refresh_token_key,
)
from app.core.security import IssuedToken
from app.models.user import User
from app.repositories.user import UserRepository


class AuthService:
    def __init__(self, db: Session, redis: Redis, settings: Settings):
        self.db = db
        self.redis = redis
        self.settings = settings
        self.users = UserRepository(db)

    def request_email_code(self, email: str) -> None:
        if self.redis.exists(email_cooldown_key(email)):
            raise VerificationCooldownError()

        code = security.generate_email_code()
        self.redis.set(email_code_key(email), code, ex=self.settings.email_verify_ttl_seconds)
        self.redis.set(email_cooldown_key(email), "1", ex=self.settings.email_verify_cooldown_seconds)
        send_verification_email(email, code)

    def verify_email_code(self, email: str, code: str) -> None:
        stored = self.redis.get(email_code_key(email))
        if stored is None or stored != code:
            raise InvalidVerificationCodeError()

        ttl = self.redis.ttl(email_code_key(email))
        self.redis.set(email_verified_key(email), "1", ex=max(ttl, 1))
        self.redis.delete(email_code_key(email))

    def signup(self, email: str, password: str, password_confirm: str) -> User:
        if password != password_confirm:
            raise PasswordMismatchError()
        if not self.redis.exists(email_verified_key(email)):
            raise EmailNotVerifiedError()
        if self.users.get_active_by_email(email) is not None:
            raise DuplicateEmailError()

        user = self.users.create(email, security.hash_password(password))
        self.db.commit()
        self.redis.delete(email_verified_key(email))
        return user

    def login(self, email: str, password: str) -> tuple[User, IssuedToken, IssuedToken]:
        user = self.users.get_active_by_email(email)
        if user is None or not security.verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        access = security.create_access_token(user.user_id)
        refresh = security.create_refresh_token(user.user_id)
        self.redis.set(
            refresh_token_key(user.user_id),
            refresh.jti,
            ex=self.settings.refresh_token_expire_days * 86400,
        )
        return user, access, refresh

    def refresh_access_token(self, refresh_token: str) -> IssuedToken:
        payload = security.decode_token(refresh_token, expected_type="refresh")
        user_id = int(payload["sub"])
        stored_jti = self.redis.get(refresh_token_key(user_id))
        if stored_jti is None or stored_jti != payload["jti"]:
            raise TokenInvalidError("리프레시 토큰이 유효하지 않습니다.")

        user = self.users.get_by_id(user_id)
        if user is None or user.status != "ACTIVE":
            raise UserWithdrawnError()

        return security.create_access_token(user_id)

    def logout(self, user_id: int, access_jti: str, access_exp: datetime) -> None:
        self.redis.delete(refresh_token_key(user_id))
        remaining = int((access_exp - datetime.now(UTC)).total_seconds())
        if remaining > 0:
            self.redis.set(access_blacklist_key(access_jti), "1", ex=remaining)

    def withdraw(self, user: User, password: str) -> None:
        if not security.verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        self.users.withdraw(user)
        self.db.commit()
        self.redis.delete(refresh_token_key(user.user_id))
