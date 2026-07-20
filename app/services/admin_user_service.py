from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.security import hash_password
from app.models.user import User, UserProfile
from app.repositories.permission_repository import PermissionRepository
from app.repositories.rol_repository import RoleRepository
from app.repositories.user import UserRepository
from app.repositories.user_rol_repository import UserRoleRepository
from app.utils.pagination import PaginationParams, paginate


class AdminUserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.user_role_repo = UserRoleRepository(db)
        self.permission_repo = PermissionRepository(db)

    async def list_users(
        self,
        params: PaginationParams,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> dict:
        stmt = await self.user_repo.base_query_admin(params.search, role, is_active)
        return await paginate(self.db, stmt, params, self._to_list_item)

    async def get_user_detail(self, user_id: UUID) -> dict:
        user = await self._get_full_or_404(user_id)
        permissions = await self.permission_repo.get_effective_codes_for_user(user.id)
        return self._to_detail(user, sorted(permissions))

    async def update_role(self, user_id: UUID, role_name: str) -> dict:
        user = await self._get_full_or_404(user_id)

        role = await self.role_repo.get_by_name(role_name)
        if role is None:
            raise BadRequestException(
                "El rol indicado no existe.",
                errors={"role": [f"'{role_name}' no es un rol válido."]},
            )

        await self.user_role_repo.remove_all_for_user(user.id)
        await self.user_role_repo.assign_role(user.id, role.id)
        await self.db.commit()

        return await self.get_user_detail(user_id)

    async def update_status(self, user_id: UUID, is_active: bool) -> dict:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundException("Usuario no encontrado.")

        await self.user_repo.set_active(user, is_active)
        await self.db.commit()

        return await self.get_user_detail(user_id)

    async def create_admin(self, data: dict[str, Any]) -> dict:
        existing = await self.user_repo.get_by_email(data["email"])
        if existing is not None:
            raise ConflictException(
                "Ya existe un usuario con ese correo.",
                errors={"email": ["El correo ya está registrado."]},
            )

        role = await self.role_repo.get_by_name("ADMIN")
        if role is None:
            raise BadRequestException("El rol 'ADMIN' no está configurado en el sistema.")

        user = await self.user_repo.create(
            data["email"], hash_password(data["password"]), email_verified=True
        )

        profile = UserProfile(
            user_id=user.id,
            first_name=data["first_name"],
            last_name=data["last_name"],
            document_type=data["document_type"],
            document_number=data["document_number"],
            phone=data["phone"],
            country=data["country"],
            department=data["department"],
            city=data["city"],
        )
        self.db.add(profile)
        await self.db.flush()

        await self.user_role_repo.assign_role(user.id, role.id)
        await self.db.commit()

        return await self.get_user_detail(user.id)

    async def _get_full_or_404(self, user_id: UUID) -> User:
        user = await self.user_repo.get_by_id_full(user_id)
        if user is None:
            raise NotFoundException("Usuario no encontrado.")
        return user

    @staticmethod
    def _to_list_item(user: User) -> dict:
        profile = user.profile
        active_role = user.user_roles[0].role.name if user.user_roles else None
        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": profile.first_name if profile else None,
            "last_name": profile.last_name if profile else None,
            "role": active_role,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "last_login": user.last_login,
            "created_at": user.created_at,
        }

    @staticmethod
    def _to_detail(user: User, permissions: list[str]) -> dict:
        profile = user.profile
        active_role = user.user_roles[0].role.name if user.user_roles else None
        return {
            "id": str(user.id),
            "email": user.email,
            "role": active_role,
            "permissions": permissions,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "last_login": user.last_login,
            "created_at": user.created_at,
            "profile": (
                {
                    "first_name": profile.first_name,
                    "last_name": profile.last_name,
                    "document_type": profile.document_type,
                    "document_number": profile.document_number,
                    "phone": profile.phone,
                    "birth_date": profile.birth_date,
                    "gender": profile.gender,
                    "country": profile.country,
                    "department": profile.department,
                    "city": profile.city,
                    "address": profile.address,
                }
                if profile
                else None
            ),
        }