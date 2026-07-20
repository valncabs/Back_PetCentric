from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel

from app.models.enums import LostReportStatus


class LostReportResponse(BaseModel):
    id: str
    pet_id: str
    created_by: str
    title: str
    description: str | None = None
    status: LostReportStatus
    lost_date: date
    reward: Decimal | None = None
    contact_phone: str | None = None
    country: str
    department: str
    city: str
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    published_at: datetime
    closed_at: datetime | None = None
    pet_name: str
    pet_species_id: str
    pet_breed_id: str | None = None
    pet_sex: str
    pet_color: str
    pet_size: str
    pet_approximate_age: int | None = None
    pet_distinctive_marks: str | None = None


class LostReportListItem(BaseModel):
    id: str
    pet_id: str
    created_by: str
    title: str
    status: LostReportStatus
    city: str
    lost_date: date
    published_at: datetime