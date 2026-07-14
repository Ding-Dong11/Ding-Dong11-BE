from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400
    code = "APP_ERROR"
    message = "요청을 처리할 수 없습니다."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)
        if message:
            self.message = message


class DuplicateEmailError(AppError):
    status_code = 409
    code = "DUPLICATE_EMAIL"
    message = "이미 가입된 이메일입니다."


class EmailNotVerifiedError(AppError):
    status_code = 400
    code = "EMAIL_NOT_VERIFIED"
    message = "이메일 인증이 필요합니다."


class InvalidVerificationCodeError(AppError):
    status_code = 400
    code = "INVALID_VERIFICATION_CODE"
    message = "인증코드가 올바르지 않거나 만료되었습니다."


class VerificationCooldownError(AppError):
    status_code = 429
    code = "VERIFICATION_COOLDOWN"
    message = "잠시 후 다시 시도해주세요."


class PasswordMismatchError(AppError):
    status_code = 400
    code = "PASSWORD_MISMATCH"
    message = "비밀번호가 일치하지 않습니다."


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"
    message = "이메일 또는 비밀번호가 올바르지 않습니다."


class TokenInvalidError(AppError):
    status_code = 401
    code = "TOKEN_INVALID"
    message = "유효하지 않은 토큰입니다."


class TokenExpiredError(AppError):
    status_code = 401
    code = "TOKEN_EXPIRED"
    message = "토큰이 만료되었습니다."


class TokenRevokedError(AppError):
    status_code = 401
    code = "TOKEN_REVOKED"
    message = "로그아웃된 토큰입니다."


class UserWithdrawnError(AppError):
    status_code = 403
    code = "USER_WITHDRAWN"
    message = "탈퇴한 계정입니다."


class DispositionNotFoundError(AppError):
    status_code = 404
    code = "DISPOSITION_NOT_FOUND"
    message = "행정처분 정보를 찾을 수 없습니다."


class StoreNotFoundError(AppError):
    status_code = 404
    code = "STORE_NOT_FOUND"
    message = "상가 정보를 찾을 수 없습니다."


class QrNotFoundError(AppError):
    status_code = 404
    code = "QR_NOT_FOUND"
    message = "유효하지 않은 QR 코드입니다."


class AlreadyVerifiedTodayError(AppError):
    status_code = 409
    code = "ALREADY_VERIFIED_TODAY"
    message = "오늘 이미 인증한 상가입니다."


class StoreQrNotFoundError(AppError):
    status_code = 404
    code = "STORE_QR_NOT_FOUND"
    message = "해당 상가에 발급된 QR 코드가 없습니다."


class SaleStoreNotFoundError(AppError):
    status_code = 404
    code = "SALE_STORE_NOT_FOUND"
    message = "세일 상점 정보를 찾을 수 없습니다."


class SaleProductNotFoundError(AppError):
    status_code = 404
    code = "SALE_PRODUCT_NOT_FOUND"
    message = "세일 상품 정보를 찾을 수 없습니다."


class SubscriptionAlreadyExistsError(AppError):
    status_code = 409
    code = "SUBSCRIPTION_ALREADY_EXISTS"
    message = "이미 관심 등록된 상점입니다."


class SubscriptionNotFoundError(AppError):
    status_code = 404
    code = "SUBSCRIPTION_NOT_FOUND"
    message = "관심 등록된 상점이 아닙니다."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message})
