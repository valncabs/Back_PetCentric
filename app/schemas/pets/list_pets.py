from decimal import Decimal
from pydantic import BaseModel

from app.models.enums import PetSex, PetSize


class PetListItem(BaseModel):
    id: str
    species_id: str
    breed_id: str | None = None
    name: str
    sex: PetSex
    color: str
    size: PetSize
    is_active: bool