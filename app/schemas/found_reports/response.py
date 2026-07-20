from datetime import date, datetime
from pydantic import BaseModel

from app.models.enums import FoundReportStatus


class FoundReportResponse(BaseModel):
    id: str
    created_by: str
    species_id: str | None = None
    lost_report_id: str | None = None
    title: str
    description: str | None = None
    status: FoundReportStatus
    found_date: date
    contact_phone: str | None = None
    country: str
    department: str
    city: str
    address: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    published_at: datetime
    closed_at: datetime | None = None


class FoundReportListItem(BaseModel):
    id: str
    created_by: str
    species_id: str | None = None
    title: str
    status: FoundReportStatus
    city: str
    found_date: date
    published_at: datetime