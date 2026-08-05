from pydantic import BaseModel

from app.models.enums import PetSex, PetSize


class PetListItem(BaseModel):
    id: str
    species_id: str
    species_name: str
    breed_id: str | None = None
    breed_name: str | None = None
    name: str
    sex: PetSex
    color: str
    size: PetSize
    is_active: bool
    primary_image_url: str | None = None