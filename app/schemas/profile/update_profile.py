from datetime import date
from pydantic import BaseModel, field_validator

from app.models.enums import DocumentType, Gender
from app.schemas.profile.get_profile import ProfileResponse
from app.schemas.profile.get_profile import ProfileResponse


class UpdateProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    document_type: DocumentType | None = None
    document_number: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    gender: Gender | None = None
    country: str | None = None
    department: str | None = None
    city: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("document_number")
    @classmethod
    def check_document_number(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("El número de documento no puede quedar vacío.")
        return value

    @field_validator("latitude")
    @classmethod
    def check_latitude(cls, value: float | None) -> float | None:
        if value is not None and not (-90 <= value <= 90):
            raise ValueError("La latitud debe estar entre -90 y 90.")
        return value

    @field_validator("longitude")
    @classmethod
    def check_longitude(cls, value: float | None) -> float | None:
        if value is not None and not (-180 <= value <= 180):
            raise ValueError("La longitud debe estar entre -180 y 180.")
        return value


class UpdateProfileResponse(ProfileResponse):
    pass

