from uuid import UUID
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserProfile


class UserProfileRepository:
    """Acceso a datos del perfil de usuario. Sin lógica de negocio, sin commit."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: UUID) -> UserProfile | None:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def exists_by_document_number(self, document_number: str, exclude_user_id: UUID | None = None) -> bool:
        stmt = select(UserProfile).where(UserProfile.document_number == document_number)
        if exclude_user_id is not None:
            stmt = stmt.where(UserProfile.user_id != exclude_user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create(self, user_id: UUID, data: dict[str, Any]) -> UserProfile:
        profile = UserProfile(user_id=user_id, **data)
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def update(self, profile: UserProfile, data: dict[str, Any]) -> UserProfile:
        for field, value in data.items():
            setattr(profile, field, value)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile