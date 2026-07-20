from datetime import datetime
from pydantic import BaseModel


class AdminUserListItem(BaseModel):
    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None
    is_active: bool
    email_verified: bool
    last_login: datetime | None = None
    created_at: datetime