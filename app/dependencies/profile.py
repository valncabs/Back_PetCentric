from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.user_rol_repository import UserRoleRepository
from app.repositories.user_profile_repository import UserProfileRepository


async def require_completed_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    profile_exists = await UserProfileRepository(db).exists_for_user(current_user.id)
    if not profile_exists:
        raise ForbiddenException(
            "Debes completar tu perfil antes de continuar.",
            errors={"profile": ["PROFILE_INCOMPLETE"]},
        )
    return current_user


async def require_completed_profile_or_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Igual que `require_completed_profile` pero exime a los admins: los
    administradores se crean sin perfil y aun así deben poder enviar
    mensajes (soporte) sin completar sus datos personales."""
    if await UserRoleRepository(db).user_has_role(current_user.id, "ADMIN"):
        return current_user
    profile_exists = await UserProfileRepository(db).exists_for_user(current_user.id)
    if not profile_exists:
        raise ForbiddenException(
            "Debes completar tu perfil antes de continuar.",
            errors={"profile": ["PROFILE_INCOMPLETE"]},
        )
    return current_user