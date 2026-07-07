from uuid import UUID
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.user import UserProfile
from app.repositories.user_profile_repository import UserProfileRepository


class ProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.profile_repo = UserProfileRepository(db)

    async def get_profile(self, user_id: UUID) -> dict:
        profile = await self.profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundException("Aún no has completado tu perfil.")
        return self._to_dict(profile)

    async def create_profile(self, user_id: UUID, data: dict[str, Any]) -> dict:
        if await self.profile_repo.get_by_user_id(user_id) is not None:
            raise ConflictException("Ya tienes un perfil creado. Usa la actualización en su lugar.")

        if await self.profile_repo.exists_by_document_number(data["document_number"]):
            raise ConflictException(
                "El número de documento ya está registrado.",
                errors={"document_number": ["Este número de documento ya está en uso."]},
            )

        profile = await self.profile_repo.create(user_id, data)
        await self.db.commit()
        return self._to_dict(profile)

    async def update_profile(self, user_id: UUID, data: dict[str, Any]) -> dict:
        profile = await self.profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundException("Aún no has completado tu perfil. Créalo primero.")

        update_data = {field: value for field, value in data.items() if value is not None}

        new_document_number = update_data.get("document_number")
        if new_document_number and new_document_number != profile.document_number:
            if await self.profile_repo.exists_by_document_number(new_document_number, exclude_user_id=user_id):
                raise ConflictException(
                    "El número de documento ya está registrado.",
                    errors={"document_number": ["Este número de documento ya está en uso."]},
                )

        profile = await self.profile_repo.update(profile, update_data)
        await self.db.commit()
        return self._to_dict(profile)

    @staticmethod
    def _to_dict(profile: UserProfile) -> dict:
        return {
            "user_id": str(profile.user_id),
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
            "latitude": profile.latitude,
            "longitude": profile.longitude,
        }