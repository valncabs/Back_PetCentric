from datetime import date
from pydantic import BaseModel, field_validator


class UpdateFoundReportRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    found_date: date | None = None
    contact_phone: str | None = None
    country: str | None = None
    department: str | None = None
    city: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("found_date")
    @classmethod
    def check_found_date(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("La fecha de encuentro no puede ser en el futuro.")
        return value