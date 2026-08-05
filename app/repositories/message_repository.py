from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication import Message


class MessageRepository:
    """Acceso a datos de mensajes. No decide transacciones: el Service
    controla cuándo hacer commit."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, conversation_id: UUID, sender_user_id: UUID, content: str
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            sender_user_id=sender_user_id,
            content=content,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    def base_query(self, conversation_id: UUID) -> Select:
        return select(Message).where(
            Message.conversation_id == conversation_id,
            Message.deleted_at.is_(None),
        )

    async def list_by_conversation(
        self, conversation_id: UUID, offset: int, limit: int
    ) -> list[Message]:
        """Página de mensajes, del más reciente al más antiguo. El cliente
        invierte el orden para mostrarlos cronológicamente."""
        stmt = (
            self.base_query(conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, conversation_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
        )
        return int((await self.db.execute(stmt)).scalar_one() or 0)

    async def last_message(self, conversation_id: UUID) -> Message | None:
        result = await self.db.execute(
            self.base_query(conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def unread_count(self, conversation_id: UUID, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_user_id != user_id,
                Message.is_read.is_(False),
                Message.deleted_at.is_(None),
            )
        )
        return int((await self.db.execute(stmt)).scalar_one() or 0)

    async def mark_conversation_read(self, conversation_id: UUID, user_id: UUID) -> list[UUID]:
        """Marca como leídos los mensajes del otro participante y devuelve
        sus ids para poder notificar al emisor en vivo."""
        result = await self.db.execute(
            select(Message.id).where(
                Message.conversation_id == conversation_id,
                Message.sender_user_id != user_id,
                Message.is_read.is_(False),
                Message.deleted_at.is_(None),
            )
        )
        message_ids = list(result.scalars().all())
        if message_ids:
            await self.db.execute(
                update(Message)
                .where(Message.id.in_(message_ids))
                .values(is_read=True)
            )
            await self.db.flush()
        return message_ids

    async def soft_delete(self, message: Message) -> None:
        from datetime import datetime, timezone

        message.deleted_at = datetime.now(timezone.utc)
        message.is_active = False
        await self.db.flush()
