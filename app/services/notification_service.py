from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.communication import Notification
from app.repositories.notification_repository import NotificationRepository
from app.utils.serializers import iso_datetime
from app.websocket import manager


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notification_repo = NotificationRepository(db)

    async def list_mine(self, user_id: UUID, page: int, page_size: int) -> dict:
        offset = (page - 1) * page_size
        notifications = await self.notification_repo.list_by_user(user_id, offset, page_size)
        total = await self.notification_repo.count_for_user(user_id)
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {
            "items": [self._to_dict(n) for n in notifications],
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": pages,
        }

    async def unread_count(self, user_id: UUID) -> int:
        return await self.notification_repo.count_unread(user_id)

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> dict:
        notification = await self._get_owned(notification_id, user_id)
        notification = await self.notification_repo.mark_read(notification)
        await self.db.commit()
        return self._to_dict(notification)

    async def mark_all_read(self, user_id: UUID) -> None:
        await self.notification_repo.mark_all_read_for_user(user_id)
        await self.db.commit()

    async def _get_owned(self, notification_id: UUID, user_id: UUID) -> Notification:
        notification = await self.notification_repo.get_by_id(notification_id)
        if notification is None:
            raise NotFoundException("Notificación no encontrada.")
        if notification.user_id != user_id:
            raise ForbiddenException("Esta notificación no te pertenece.")
        return notification

    @staticmethod
    def _to_dict(notification: Notification) -> dict:
        return {
            "id": str(notification.id),
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "is_read": notification.is_read,
            "conversation_id": (
                str(notification.conversation_id)
                if notification.conversation_id is not None
                else None
            ),
            "lost_report_id": (
                str(notification.lost_report_id)
                if notification.lost_report_id is not None
                else None
            ),
            "created_at": iso_datetime(notification.created_at),
        }
