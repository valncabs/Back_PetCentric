from pydantic import BaseModel, EmailStr, field_validator
from app.utils.validators import validate_password_strength


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_password_strength(value)


class RegisterResponse(BaseModel):
    id: str
    email: str
    email_verified: bool