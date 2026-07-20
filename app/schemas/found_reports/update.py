from datetime import date
from pydantic import BaseModel


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