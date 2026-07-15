from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends, Request
from redis import Redis
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.exceptions import TokenInvalidError, TokenRevokedError, UserWithdrawnError
from app.core.redis import get_redis
from app.core.redis_keys import access_blacklist_key
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user import UserRepository


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise TokenInvalidError("인증 토큰이 없습니다.")
    return auth_header.removeprefix("Bearer ").strip()


@dataclass
class AuthContext:
    user: User
    jti: str
    exp: datetime


def get_current_auth_context(
    request: Request,
    db: Session = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> AuthContext:
    token = _extract_bearer_token(request)
    payload = decode_token(token, expected_type="access")
    jti = payload["jti"]
    if redis.exists(access_blacklist_key(jti)):
        raise TokenRevokedError()

    user = UserRepository(db).get_by_id(int(payload["sub"]))
    if user is None:
        raise TokenInvalidError()
    if user.status != "ACTIVE":
        raise UserWithdrawnError()

    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    return AuthContext(user=user, jti=jti, exp=exp)


def get_current_user(ctx: AuthContext = Depends(get_current_auth_context)) -> User:
    return ctx.user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> User | None:
    """비로그인 허용 의존성. 토큰이 없거나 유효하지 않으면 None 반환."""
    try:
        ctx = get_current_auth_context(request, db, redis)
        return ctx.user
    except Exception:
        return None
