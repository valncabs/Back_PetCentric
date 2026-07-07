from decimal import Decimal
from pydantic import BaseModel, field_validator

from app.models.enums import PetSex, PetSize


class CreatePetRequest(BaseModel):
    species_id: str
    breed_id: str | None = None
    name: str
    sex: PetSex
    color: str
    size: PetSize
    weight: Decimal | None = None
    approximate_age: int | None = None
    microchip_number: str | None = None
    sterilized: bool = False
    distinctive_marks: str | None = None
    description: str | None = None

    @field_validator("name", "color")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo no puede estar vacío.")
        return value

    @field_validator("approximate_age")
    @classmethod
    def check_age(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("La edad aproximada no puede ser negativa.")
        return value


class PetResponse(BaseModel):
    id: str
    owner_user_id: str
    species_id: str
    breed_id: str | None = None
    name: str
    sex: PetSex
    color: str
    size: PetSize
    weight: Decimal | None = None
    approximate_age: int | None = None
    microchip_number: str | None = None
    sterilized: bool
    distinctive_marks: str | None = None
    description: str | None = None
    is_active: bool