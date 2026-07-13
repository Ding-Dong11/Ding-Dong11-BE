from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.deps import AuthContext, get_current_auth_context
from app.core.exceptions import TokenInvalidError
from app.core.redis import get_redis
from app.schemas.auth import (
    EmailCodeRequest,
    EmailVerifyRequest,
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
    WithdrawRequest,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def get_auth_service(
    db: Session = Depends(get_session),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(db=db, redis=redis, settings=settings)


def _set_auth_cookies(
    response: Response, settings: Settings, access_token: str, refresh_token: str
) -> None:
    # access_token: 서버->클라이언트는 쿠키로 전달하되, 클라이언트->서버 요청은 Authorization
    # Bearer 헤더로만 받는다(get_current_auth_context). 따라서 프론트가 값을 읽어 헤더에
    # 실어 보낼 수 있도록 httponly=False로 발급한다.
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=False,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        secure=True,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.post("/email/code", status_code=204)
def request_email_code(body: EmailCodeRequest, service: AuthService = Depends(get_auth_service)) -> None:
    service.request_email_code(body.email)


@router.post("/email/verify", status_code=204)
def verify_email_code(body: EmailVerifyRequest, service: AuthService = Depends(get_auth_service)) -> None:
    service.verify_email_code(body.email, body.code)


@router.post("/signup", response_model=SignupResponse, status_code=201)
def signup(body: SignupRequest, service: AuthService = Depends(get_auth_service)) -> SignupResponse:
    user = service.signup(body.email, body.password, body.password_confirm)
    return SignupResponse(user_id=user.user_id, email=user.email)


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    user, access, refresh = service.login(body.email, body.password)
    _set_auth_cookies(response, settings, access.token, refresh.token)
    return LoginResponse(user_id=user.user_id, email=user.email)


@router.post("/refresh", status_code=204)
def refresh_token(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    service: AuthService = Depends(get_auth_service),
) -> None:
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise TokenInvalidError("리프레시 토큰이 없습니다.")

    access = service.refresh_access_token(token)
    response.set_cookie(
        ACCESS_COOKIE,
        access.token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=False,
        secure=True,
        samesite="lax",
        path="/",
    )


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    ctx: AuthContext = Depends(get_current_auth_context),
    service: AuthService = Depends(get_auth_service),
) -> None:
    service.logout(ctx.user.user_id, ctx.jti, ctx.exp)
    _clear_auth_cookies(response)


@router.post("/withdraw", status_code=204)
def withdraw(
    body: WithdrawRequest,
    response: Response,
    ctx: AuthContext = Depends(get_current_auth_context),
    service: AuthService = Depends(get_auth_service),
) -> None:
    service.withdraw(ctx.user, body.password)
    service.logout(ctx.user.user_id, ctx.jti, ctx.exp)
    _clear_auth_cookies(response)
