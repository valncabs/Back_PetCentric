from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import UserRole


class UserRoleRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def assign_role(self, user_id: UUID, role_id: UUID) -> UserRole:
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
        )
        self.db.add(user_role)
        await self.db.flush()
        return user_role

    async def get_by_user_id(self, user_id: UUID) -> list[UserRole]:
        result = await self.db.execute(select(UserRole).where(UserRole.user_id == user_id))
        return list(result.scalars().all())

    async def remove_all_for_user(self, user_id: UUID) -> None:
        """Borra todas las asignaciones de rol del usuario antes de asignar
        una nueva. El sistema modela roles N:N pero en la práctica cada
        usuario opera con un único rol activo a la vez."""
        roles = await self.get_by_user_id(user_id)
        for user_role in roles:
            await self.db.delete(user_role)
        await self.db.flush()