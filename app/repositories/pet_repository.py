from uuid import UUID
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pet import Pet

_EAGER_OPTIONS = (
    selectinload(Pet.species),
    selectinload(Pet.breed),
    selectinload(Pet.primary_image),
)


class PetRepository:
    """Acceso a datos de mascotas. Sin lógica de negocio, sin commit."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, owner_user_id: UUID, data: dict[str, Any]) -> Pet:
        pet = Pet(owner_user_id=owner_user_id, **data)
        self.db.add(pet)
        await self.db.flush()
        return await self._get_with_relations(pet.id)

    async def get_by_id_for_owner(self, pet_id: UUID, owner_user_id: UUID) -> Pet | None:
        result = await self.db.execute(
            select(Pet)
            .options(*_EAGER_OPTIONS)
            .where(
                Pet.id == pet_id,
                Pet.owner_user_id == owner_user_id,
                Pet.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def base_query_for_owner(
        self,
        owner_user_id: UUID,
        search: str | None = None,
        sort: str | None = None,
        order: str = "asc",
    ) -> Select:
        stmt = (
            select(Pet)
            .options(*_EAGER_OPTIONS)
            .where(Pet.owner_user_id == owner_user_id, Pet.deleted_at.is_(None))
        )

        if search:
            stmt = stmt.where(Pet.name.ilike(f"%{search}%"))

        sortable_columns = {
            "name": Pet.name,
            "created_at": Pet.created_at,
            "size": Pet.size,
            "sex": Pet.sex,
        }
        column = sortable_columns.get(sort, Pet.created_at)
        stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())

        return stmt

    async def exists_by_microchip(self, microchip_number: str, exclude_pet_id: UUID | None = None) -> bool:
        stmt = select(Pet).where(Pet.microchip_number == microchip_number)
        if exclude_pet_id is not None:
            stmt = stmt.where(Pet.id != exclude_pet_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update(self, pet: Pet, data: dict[str, Any]) -> Pet:
        for field, value in data.items():
            setattr(pet, field, value)
        await self.db.flush()
        return await self._get_with_relations(pet.id)

    async def soft_delete(self, pet: Pet) -> None:
        from datetime import datetime, timezone
        pet.deleted_at = datetime.now(timezone.utc)
        pet.is_active = False
        await self.db.flush()

    async def get_by_id_ignoring_owner(self, pet_id: UUID) -> Pet | None:
        """Lee una mascota sin filtrar por dueño. Uso exclusivo para exponer
        datos públicos y seguros (nombre, especie, etc.) desde un reporte
        público como lost_reports — nunca para operaciones de escritura ni
        para exponer campos sensibles como microchip_number."""
        result = await self.db.execute(
            select(Pet).options(*_EAGER_OPTIONS).where(Pet.id == pet_id, Pet.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def _get_with_relations(self, pet_id: UUID) -> Pet:
        result = await self.db.execute(
            select(Pet)
            .options(*_EAGER_OPTIONS)
            .where(Pet.id == pet_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one()