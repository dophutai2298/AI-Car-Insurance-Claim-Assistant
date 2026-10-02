from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import UserRole


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class UserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole


class UserSecurityUpdateRequest(BaseModel):
    password: str | None = Field(default=None, min_length=6, max_length=128)
    is_active: bool | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class MfaEnrollRequest(BaseModel):
    secret: str = Field(min_length=16, max_length=128)
    code: str = Field(pattern=r"^\d{6}$")


class MfaRecoveryCodesResponse(BaseModel):
    recovery_codes: list[str]


class MfaChallengeRequest(BaseModel):
    challenge_token: str = Field(min_length=20, max_length=2048)
    code: str | None = Field(default=None, pattern=r"^\d{6}$")
    recovery_code: str | None = Field(default=None, min_length=8, max_length=64)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str
    full_name: str
    role: UserRole


class LoginResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse
    mfa_required: bool = False
    mfa_challenge_token: str | None = None
