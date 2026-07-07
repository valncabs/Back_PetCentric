from uuid import UUID

from sqlalchemy import select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Permission, RolePermission, UserPermission, UserRole


class PermissionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_effective_codes_for_user(self, user_id: UUID) -> set[str]:
        """Devuelve el conjunto de códigos de permiso efectivos de un usuario:
        los de su rol + los asignados directamente. Una sola consulta UNION."""

        from_role = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
        )

        from_direct = (
            select(Permission.code)
            .join(UserPermission, UserPermission.permission_id == Permission.id)
            .where(UserPermission.user_id == user_id, UserPermission.is_active.is_(True))
        )

        result = await self.db.execute(union(from_role, from_direct))
        return {row[0] for row in result.all()}

    async def list_all(self) -> list[Permission]:
        result = await self.db.execute(select(Permission).where(Permission.is_active.is_(True)))
        return list(result.scalars().all())