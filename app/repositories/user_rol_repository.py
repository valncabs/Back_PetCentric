from app.models.auth import UserRole
from sqlalchemy.ext.asyncio import AsyncSession

class UserRoleRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def assign_role(self, user_id, role_id):
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
        )

        self.db.add(user_role)
        await self.db.flush()

        return user_role