from datetime import date
from decimal import Decimal
from pydantic import BaseModel, field_validator


class CreateLostReportRequest(BaseModel):
    pet_id: str
    title: str
    description: str | None = None
    lost_date: date
    reward: Decimal | None = None
    contact_phone: str | None = None
    country: str
    department: str
    city: str
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None

    @field_validator("title", "country", "department", "city")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo no puede estar vacío.")
        return value

    @field_validator("reward")
    @classmethod
    def check_reward(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("La recompensa no puede ser negativa.")
        return value