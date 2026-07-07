from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.repositories.species_repository import SpeciesRepository


class CatalogService:
    def __init__(self, db: AsyncSession) -> None:
        self.species_repo = SpeciesRepository(db)

    async def list_species(self) -> list[dict]:
        species = await self.species_repo.list_active()
        return [{"id": str(s.id), "name": s.name} for s in species]

    async def list_breeds(self, species_id: UUID) -> list[dict]:
        species = await self.species_repo.get_by_id(species_id)
        if species is None:
            raise NotFoundException("Especie no encontrada.")

        breeds = await self.species_repo.list_breeds_by_species(species_id)
        return [{"id": str(b.id), "species_id": str(b.species_id), "name": b.name} for b in breeds]