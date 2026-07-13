from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, ValidationInfo, field_validator


class EmailCodeRequest(BaseModel):
    email: EmailStr


class EmailVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=20)
    password_confirm: str = Field(min_length=8, max_length=20)

    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        password = info.data.get("password")
        if password is not None and v != password:
            raise ValueError("password_confirm does not match password")
        return v


class SignupResponse(BaseModel):
    user_id: int
    email: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=20)


class LoginResponse(BaseModel):
    user_id: int
    email: str


class WithdrawRequest(BaseModel):
    password: str = Field(min_length=8, max_length=20)
