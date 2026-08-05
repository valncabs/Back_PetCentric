from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication import Notification
from app.models.enums import NotificationType


class NotificationRepository:
    """Acceso a datos de notificaciones. No decide transacciones: el Service
    controla cuándo hacer commit."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: UUID,
        title: str,
        message: str,
        type_: NotificationType,
        conversation_id: UUID | None = None,
        lost_report_id: UUID | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type_,
            conversation_id=conversation_id,
            lost_report_id=lost_report_id,
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    def base_query(self, user_id: UUID) -> Select:
        return (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
        )

    async def list_by_user(self, user_id: UUID, offset: int, limit: int) -> list[Notification]:
        result = await self.db.execute(
            self.base_query(user_id).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count_unread(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        return int((await self.db.execute(stmt)).scalar_one() or 0)

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        return await self.db.get(Notification, notification_id)

    async def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        await self.db.flush()
        return notification

    async def mark_all_read_for_user(self, user_id: UUID) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        await self.db.flush()
        return result.rowcount or 0

    async def mark_read_for_conversation(self, conversation_id: UUID, user_id: UUID) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.conversation_id == conversation_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await self.db.flush()
        return result.rowcount or 0
