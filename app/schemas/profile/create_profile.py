from datetime import date
from pydantic import BaseModel, field_validator

from app.models.enums import DocumentType, Gender


class CreateProfileRequest(BaseModel):
    """
    Campos obligatorios reflejan exactamente las columnas NOT NULL de
    UserProfile. La existencia de este registro completo es lo que el
    sistema considera "perfil completado" (ver dependencies/profile.py).
    """
    document_type: DocumentType
    document_number: str
    first_name: str
    last_name: str
    phone: str
    country: str
    department: str
    city: str

    # Verdaderamente opcionales a nivel de negocio y de BD
    birth_date: date | None = None
    gender: Gender | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("document_number", "first_name", "last_name", "phone", "country", "department", "city")
    @classmethod
    def check_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo es obligatorio.")
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

    @field_validator("birth_date")
    @classmethod
    def check_birth_date(cls, value: date | None) -> date | None:
        if value is None:
            return value
        today = date.today()
        if value > today:
            raise ValueError("La fecha de nacimiento no puede ser en el futuro.")
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 15:
            raise ValueError("Debes tener al menos 15 años para registrarte.")
        return value


class CreateProfileResponse(BaseModel):
    user_id: str
    document_type: DocumentType
    document_number: str
    first_name: str
    last_name: str
    phone: str
    birth_date: date | None = None
    gender: Gender | None = None
    country: str
    department: str
    city: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None