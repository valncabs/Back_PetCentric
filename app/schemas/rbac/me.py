from pydantic import BaseModel


class MyPermissionsResponse(BaseModel):
    role: str | None = None
    permissions: list[str]