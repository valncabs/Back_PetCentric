from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.permission_repository import PermissionRepository


class RBACService:
    def __init__(self, db: AsyncSession) -> None:
        self.permission_repo = PermissionRepository(db)

    async def get_effective_permissions(self, user_id: UUID) -> set[str]:
        return await self.permission_repo.get_effective_codes_for_user(user_id)

    async def has_permission(self, user_id: UUID, code: str) -> bool:
        codes = await self.get_effective_permissions(user_id)
        return code in codes