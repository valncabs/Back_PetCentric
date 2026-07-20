from datetime import date
from pydantic import BaseModel, field_validator


class CreateFoundReportRequest(BaseModel):
    species_id: str
    lost_report_id: str | None = None
    title: str
    description: str | None = None
    found_date: date
    contact_phone: str | None = None
    country: str
    department: str
    city: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("title", "country", "department", "city")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo no puede estar vacío.")
        return value