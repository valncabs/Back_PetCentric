from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import Role, UserRole
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

    async def create(self, email: str, password_hash: str, email_verified: bool = False) -> User:
        """Firma extendida: create_admin necesita marcar email_verified=True
        directamente, sin pasar por el flujo de verificación por correo."""
        user = User(email=email, password_hash=password_hash, email_verified=email_verified)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_by_id_full(self, user_id: UUID) -> User | None:
        """Versión con eager-load de perfil y roles, para el detalle admin
        y para reconstruir la respuesta tras cambiar rol/estado."""
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.profile),
                selectinload(User.user_roles).selectinload(UserRole.role),
            )
            .where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def base_query_admin(
        self,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ):
        stmt = (
            select(User)
            .where(User.deleted_at.is_(None))
            .options(
                selectinload(User.profile),
                selectinload(User.user_roles).selectinload(UserRole.role),
            )
        )

        if search:
            stmt = stmt.where(User.email.ilike(f"%{search}%"))
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if role:
            stmt = stmt.where(
                User.id.in_(
                    select(UserRole.user_id)
                    .join(Role, Role.id == UserRole.role_id)
                    .where(Role.name == role)
                )
            )

        return stmt.order_by(User.created_at.desc())

    async def set_active(self, user: User, is_active: bool) -> None:
        user.is_active = is_active
        await self.db.flush()