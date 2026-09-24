from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db import get_db
from app.models import User
from app.api.permissions import Permission, has_permission
from app.services.auth import AuthService

bearer_scheme = HTTPBearer(auto_error=False)
DatabaseSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    user = (
        AuthService(session, settings).user_from_token(credentials.credentials)
        if credentials and credentials.scheme.lower() == "bearer"
        else None
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_permission(permission: Permission):
    def check(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not has_permission(current_user.role, permission):
            detail = "Admin access required" if permission is Permission.ADMIN else "Insufficient permissions"
            raise HTTPException(status_code=403, detail=detail)
        return current_user

    return check


require_admin = require_permission(Permission.ADMIN)
require_analysis = require_permission(Permission.ANALYSIS)
require_ai_review = require_permission(Permission.AI_REVIEW)
require_human_review = require_permission(Permission.HUMAN_REVIEW)
require_analysis_support = require_permission(Permission.ANALYSIS_SUPPORT)


AdminUser = Annotated[User, Depends(require_admin)]
AnalysisUser = Annotated[User, Depends(require_analysis)]
AiReviewUser = Annotated[User, Depends(require_ai_review)]
HumanReviewUser = Annotated[User, Depends(require_human_review)]
AnalysisSupportUser = Annotated[User, Depends(require_analysis_support)]
