from uuid import UUID

from pydantic import BaseModel, field_validator


class SendMessageRequest(BaseModel):
    conversation_id: UUID
    content: str

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El mensaje no puede estar vacío.")
        if len(value) > 2000:
            raise ValueError("El mensaje no puede superar los 2000 caracteres.")
        return value
