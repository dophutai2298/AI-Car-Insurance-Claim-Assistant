from enum import Enum

from app.models import UserRole


class Permission(str, Enum):
    ADMIN = "admin"
    ANALYSIS = "analysis"
    AI_REVIEW = "ai_review"
    HUMAN_REVIEW = "human_review"
    ANALYSIS_SUPPORT = "analysis_support"


ROLE_PERMISSIONS = {
    UserRole.ADMIN: frozenset(Permission),
    UserRole.ADJUSTER: frozenset(
        {
            Permission.ANALYSIS,
            Permission.AI_REVIEW,
            Permission.HUMAN_REVIEW,
            Permission.ANALYSIS_SUPPORT,
        }
    ),
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
