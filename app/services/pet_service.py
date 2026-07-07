from uuid import UUID
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.pet import Pet
from app.repositories.pet_repository import PetRepository
from app.repositories.species_repository import SpeciesRepository
from app.utils.pagination import PaginationParams, paginate


class PetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.pet_repo = PetRepository(db)
        self.species_repo = SpeciesRepository(db)

    async def create_pet(self, owner_user_id: UUID, data: dict[str, Any]) -> dict:
        await self._validate_species_and_breed(data.get("species_id"), data.get("breed_id"))
        await self._validate_microchip(data.get("microchip_number"))

        pet = await self.pet_repo.create(owner_user_id, data)
        await self.db.commit()
        return self._to_dict(pet)

    async def get_pet(self, pet_id: UUID, owner_user_id: UUID) -> dict:
        pet = await self.pet_repo.get_by_id_for_owner(pet_id, owner_user_id)
        if pet is None:
            raise NotFoundException("Mascota no encontrada.")
        return self._to_dict(pet)

    async def list_pets(self, owner_user_id: UUID, params: PaginationParams) -> dict:
        stmt = self.pet_repo.base_query_for_owner(
            owner_user_id, params.search, params.sort, params.order
        )
        return await paginate(self.db, stmt, params, self._to_list_item)

    async def update_pet(self, pet_id: UUID, owner_user_id: UUID, data: dict[str, Any]) -> dict:
        pet = await self.pet_repo.get_by_id_for_owner(pet_id, owner_user_id)
        if pet is None:
            raise NotFoundException("Mascota no encontrada.")

        update_data = {field: value for field, value in data.items() if value is not None}

        if "species_id" in update_data or "breed_id" in update_data:
            species_id = update_data.get("species_id", pet.species_id)
            breed_id = update_data.get("breed_id", pet.breed_id)
            await self._validate_species_and_breed(species_id, breed_id)

        new_microchip = update_data.get("microchip_number")
        if new_microchip and new_microchip != pet.microchip_number:
            await self._validate_microchip(new_microchip, exclude_pet_id=pet.id)

        pet = await self.pet_repo.update(pet, update_data)
        await self.db.commit()
        return self._to_dict(pet)

    async def delete_pet(self, pet_id: UUID, owner_user_id: UUID) -> None:
        pet = await self.pet_repo.get_by_id_for_owner(pet_id, owner_user_id)
        if pet is None:
            raise NotFoundException("Mascota no encontrada.")

        await self.pet_repo.soft_delete(pet)
        await self.db.commit()

    # ---------- Validaciones internas ----------

    async def _validate_species_and_breed(self, species_id: Any, breed_id: Any) -> None:
        if species_id is None:
            return
        species = await self.species_repo.get_by_id(species_id)
        if species is None or not species.is_active:
            raise BadRequestException(
                "Especie inválida.", errors={"species_id": ["La especie seleccionada no existe."]}
            )

        if breed_id is not None:
            breed = await self.species_repo.get_breed_by_id(breed_id)
            if breed is None or not breed.is_active or breed.species_id != species.id:
                raise BadRequestException(
                    "Raza inválida.", errors={"breed_id": ["La raza no pertenece a la especie seleccionada."]}
                )

    async def _validate_microchip(self, microchip_number: str | None, exclude_pet_id: UUID | None = None) -> None:
        if not microchip_number:
            return
        if await self.pet_repo.exists_by_microchip(microchip_number, exclude_pet_id):
            raise ConflictException(
                "El número de microchip ya está registrado.",
                errors={"microchip_number": ["Este microchip ya pertenece a otra mascota."]},
            )

    @staticmethod
    def _to_dict(pet: Pet) -> dict:
        return {
            "id": str(pet.id),
            "owner_user_id": str(pet.owner_user_id),
            "species_id": str(pet.species_id),
            "breed_id": str(pet.breed_id) if pet.breed_id else None,
            "name": pet.name,
            "sex": pet.sex,
            "color": pet.color,
            "size": pet.size,
            "weight": pet.weight,
            "approximate_age": pet.approximate_age,
            "microchip_number": pet.microchip_number,
            "sterilized": pet.sterilized,
            "distinctive_marks": pet.distinctive_marks,
            "description": pet.description,
            "is_active": pet.is_active,
        }

    @staticmethod
    def _to_list_item(pet: Pet) -> dict:
        return {
            "id": str(pet.id),
            "species_id": str(pet.species_id),
            "breed_id": str(pet.breed_id) if pet.breed_id else None,
            "name": pet.name,
            "sex": pet.sex,
            "color": pet.color,
            "size": pet.size,
            "is_active": pet.is_active,
        }