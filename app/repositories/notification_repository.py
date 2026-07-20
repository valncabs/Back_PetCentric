from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication import Notification
from app.models.enums import NotificationType


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user_id: UUID, title: str, message: str, type_: NotificationType) -> Notification:
        notification = Notification(user_id=user_id, title=title, message=message, type=type_)
        self.db.add(notification)
        await self.db.flush()
        return notification