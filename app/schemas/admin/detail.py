from datetime import date, datetime
from pydantic import BaseModel

from app.models.enums import DocumentType, Gender


class AdminUserProfileResponse(BaseModel):
    first_name: str
    last_name: str
    document_type: DocumentType
    document_number: str
    phone: str
    birth_date: date | None = None
    gender: Gender | None = None
    country: str
    department: str
    city: str
    address: str | None = None


class AdminUserDetailResponse(BaseModel):
    id: str
    email: str
    role: str | None = None
    permissions: list[str]
    is_active: bool
    email_verified: bool
    last_login: datetime | None = None
    created_at: datetime
    profile: AdminUserProfileResponse | None = None