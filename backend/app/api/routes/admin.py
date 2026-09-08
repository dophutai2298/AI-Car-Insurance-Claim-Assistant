from fastapi import APIRouter

from app.api.dependencies import AdminUser

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/access-check")
def admin_access_check(current_user: AdminUser) -> dict[str, str]:
    return {"status": "ok", "role": current_user.role.value}
