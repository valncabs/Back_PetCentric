from pydantic import BaseModel, Field


class UpdateUserRoleRequest(BaseModel):
    role: str = Field(..., description="Nombre exacto del rol, ej. 'ADMIN' o 'USER'.")