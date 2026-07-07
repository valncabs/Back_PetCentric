from typing import Callable

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.rbac_service import RBACService


def require_permission(permission_code: str) -> Callable:
    """Factory de dependencia FastAPI: exige que el usuario autenticado tenga
    el permiso indicado (por rol o asignación directa). Uso:

        @router.post("/admin/roles", dependencies=[Depends(require_permission("roles.create"))])
    """

    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        has_access = await RBACService(db).has_permission(current_user.id, permission_code)
        if not has_access:
            raise ForbiddenException(
                "No tienes permiso para realizar esta acción.",
                errors={"permission": [f"Se requiere el permiso '{permission_code}'."]},
            )

    return dependency