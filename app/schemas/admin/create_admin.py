from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import DocumentType
from app.utils.validators import validate_password_strength


class CreateAdminRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str
    last_name: str
    document_type: DocumentType
    document_number: str
    phone: str
    country: str
    department: str
    city: str

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password_strength(value)