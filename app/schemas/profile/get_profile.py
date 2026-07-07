from datetime import date
from pydantic import BaseModel

from app.models.enums import DocumentType, Gender


class ProfileResponse(BaseModel):
    user_id: str
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