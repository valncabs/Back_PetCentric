from pydantic import BaseModel, EmailStr, Field

from app.models.enums import DocumentType


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