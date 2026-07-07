from pydantic import BaseModel


class SpeciesResponse(BaseModel):
    id: str
    name: str


class BreedResponse(BaseModel):
    id: str
    species_id: str
    name: str