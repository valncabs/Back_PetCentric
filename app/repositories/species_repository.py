from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pet import Breed, Species


class SpeciesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active(self) -> list[Species]:
        result = await self.db.execute(
            select(Species).where(Species.is_active.is_(True)).order_by(Species.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, species_id: UUID) -> Species | None:
        return await self.db.get(Species, species_id)

    async def list_breeds_by_species(self, species_id: UUID) -> list[Breed]:
        result = await self.db.execute(
            select(Breed)
            .where(Breed.species_id == species_id, Breed.is_active.is_(True))
            .order_by(Breed.name)
        )
        return list(result.scalars().all())

    async def get_breed_by_id(self, breed_id: UUID) -> Breed | None:
        return await self.db.get(Breed, breed_id)