from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class UpdateLostReportRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    lost_date: date | None = None
    reward: Decimal | None = None
    contact_phone: str | None = None
    country: str | None = None
    department: str | None = None
    city: str | None = None
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None