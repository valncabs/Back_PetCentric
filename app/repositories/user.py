from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import UserRole
from app.models.user import User


class UserRepository:
    """Acceso a datos de usuarios. No decide transacciones: el Service
    controla cuándo hacer commit."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_email_with_roles(self, email: str) -> User | None:
        """Versión con eager-load de roles, necesaria para el login:
        acceder a relaciones lazy en un contexto async fuera de este
        método revienta con MissingGreenlet."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create(self, email: str, password_hash: str) -> User:
        user = User(email=email, password_hash=password_hash, email_verified=False)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def mark_email_verified(self, user: User) -> None:
        user.email_verified = True
        await self.db.flush()

    async def update_password(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        await self.db.flush()

    async def update_last_login(self, user: User) -> None:
        user.last_login = datetime.now(timezone.utc)
        await self.db.flush()