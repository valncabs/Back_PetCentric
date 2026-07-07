from decimal import Decimal
from pydantic import BaseModel, field_validator

from app.models.enums import PetSex, PetSize


class UpdatePetRequest(BaseModel):
    species_id: str | None = None
    breed_id: str | None = None
    name: str | None = None
    sex: PetSex | None = None
    color: str | None = None
    size: PetSize | None = None
    weight: Decimal | None = None
    approximate_age: int | None = None
    microchip_number: str | None = None
    sterilized: bool | None = None
    distinctive_marks: str | None = None
    description: str | None = None

    @field_validator("name", "color")
    @classmethod
    def not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Este campo no puede quedar vacío.")
        return value

    @field_validator("approximate_age")
    @classmethod
    def check_age(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("La edad aproximada no puede ser negativa.")
        return value