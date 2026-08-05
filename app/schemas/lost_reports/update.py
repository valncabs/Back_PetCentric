from datetime import date
from decimal import Decimal
from pydantic import BaseModel, field_validator


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

    @field_validator("reward")
    @classmethod
    def check_reward(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if value < 0:
            raise ValueError("La recompensa no puede ser negativa.")
        if value > Decimal("99999999.99"):
            raise ValueError("La recompensa no puede superar los $99.999.999.")
        if value.as_tuple().exponent < -2:
            raise ValueError("La recompensa admite máximo 2 decimales.")
        return value

    @field_validator("lost_date")
    @classmethod
    def check_lost_date(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("La fecha de pérdida no puede ser en el futuro.")
        return value