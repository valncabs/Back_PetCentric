from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.auth import Role, UserRole
from app.models.user import User
from app.services.rbac_service import RBACService
from app.utils.response import success_response

router = APIRouter(prefix="/rbac", tags=["RBAC"])


@router.get("/me")
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    permissions = await RBACService(db).get_effective_permissions(current_user.id)

    result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    )
    role_name = result.scalar_one_or_none()

    data = {"role": role_name, "permissions": sorted(permissions)}
    return success_response(data=data, message="Permisos obtenidos correctamente.")
