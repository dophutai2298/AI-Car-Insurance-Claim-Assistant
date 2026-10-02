from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import AdminUser, AnalysisSupportUser
from app.core.config import Settings, get_settings
from app.db import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MfaChallengeRequest,
    MfaEnrollRequest,
    MfaRecoveryCodesResponse,
    RefreshTokenRequest,
    UserCreateRequest,
    UserResponse,
    UserSecurityUpdateRequest,
)
from app.services.auth import AuthRateLimitExceeded, AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _tokens_response(user, access_token: str, refresh_token: str, settings: Settings) -> LoginResponse:
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_minutes * 60,
        user=UserResponse.model_validate(user),
    )


def _rate_limit(service: AuthService, operation: str, identifier: str) -> None:
    try:
        service.check_rate_limit(operation, identifier)
    except AuthRateLimitExceeded as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts",
            headers={"Retry-After": str(error.retry_after)},
        ) from error


def _client_identifier(request: Request) -> str:
    return request.client.host if request.client else "unknown-client"


@router.post("/login", response_model=LoginResponse)
def login(
    request: Request,
    credentials: LoginRequest,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    service = AuthService(session, settings)
    rate_limit_key = f"{credentials.email}:{_client_identifier(request)}"
    _rate_limit(service, "login", rate_limit_key)
    user = service.authenticate(credentials.email, credentials.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    service.clear_rate_limit("login", rate_limit_key)
    if user.mfa_enabled:
        return LoginResponse(
            user=UserResponse.model_validate(user),
            mfa_required=True,
            mfa_challenge_token=service.create_mfa_challenge_token(user),
        )
    access_token, refresh_token = service.issue_session(user)
    return _tokens_response(user, access_token, refresh_token, settings)


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    http_request: Request,
    request: RefreshTokenRequest,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    service = AuthService(session, settings)
    client_identifier = _client_identifier(http_request)
    _rate_limit(service, "refresh", client_identifier)
    result = service.rotate_refresh_token(request.refresh_token)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    service.clear_rate_limit("refresh", client_identifier)
    user, access_token, refresh_token = result
    return _tokens_response(user, access_token, refresh_token, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: RefreshTokenRequest,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    AuthService(session, settings).logout(request.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/mfa/challenge", response_model=LoginResponse)
def challenge_mfa(
    http_request: Request,
    request: MfaChallengeRequest,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    service = AuthService(session, settings)
    client_identifier = _client_identifier(http_request)
    _rate_limit(service, "mfa", client_identifier)
    result = service.complete_mfa_challenge(
        request.challenge_token, code=request.code, recovery_code=request.recovery_code
    )
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid MFA challenge")
    service.clear_rate_limit("mfa", client_identifier)
    user, access_token, refresh_token = result
    return _tokens_response(user, access_token, refresh_token, settings)


@router.post("/mfa/enroll", response_model=MfaRecoveryCodesResponse)
def enroll_mfa(
    http_request: Request,
    request: MfaEnrollRequest,
    current_user: AnalysisSupportUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MfaRecoveryCodesResponse:
    service = AuthService(session, settings)
    client_identifier = f"{current_user.email}:{_client_identifier(http_request)}"
    _rate_limit(service, "mfa_enroll", client_identifier)
    recovery_codes = service.enroll_mfa(
        current_user, request.secret, request.code
    )
    if recovery_codes is None:
        raise HTTPException(status_code=422, detail="Invalid MFA secret or code")
    service.clear_rate_limit("mfa_enroll", client_identifier)
    return MfaRecoveryCodesResponse(recovery_codes=recovery_codes)


@router.get("/me", response_model=UserResponse)
def current_session(current_user: AnalysisSupportUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    account: UserCreateRequest,
    _admin_user: AdminUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    user = AuthService(session, settings).create_user(account)
    if user is None:
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    return UserResponse.model_validate(user)


@router.patch("/users/{user_email}", response_model=UserResponse)
def update_user_security(
    user_email: str,
    request: UserSecurityUpdateRequest,
    _admin_user: AdminUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    user = AuthService(session, settings).update_user_security(user_email, request)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)
