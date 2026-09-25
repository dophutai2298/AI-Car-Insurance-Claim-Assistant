from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import AdminUser, AnalysisSupportUser
from app.core.config import Settings, get_settings
from app.db import get_db
from app.schemas.auth import LoginRequest, LoginResponse, UserCreateRequest, UserResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    credentials: LoginRequest,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    service = AuthService(session, settings)
    user = service.authenticate(credentials.email, credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return LoginResponse(
        access_token=service.create_access_token(user),
        user=UserResponse.model_validate(user),
    )


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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    return UserResponse.model_validate(user)
