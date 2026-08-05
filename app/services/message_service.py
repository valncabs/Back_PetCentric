from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.communication import Message
from app.models.enums import NotificationType
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.notification_repository import NotificationRepository
from app.utils.serializers import iso_datetime
from app.websocket import manager


class MessageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        self.notification_repo = NotificationRepository(db)

    async def send_message(self, actor_id: UUID, conversation_id: UUID, content: str) -> dict:
        if not await self.conversation_repo.is_participant(conversation_id, actor_id):
            raise ForbiddenException("No eres participante de esta conversación.")

        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundException("Conversación no encontrada.")

        participant_ids = await self.conversation_repo.participant_ids(conversation_id)
        other_ids = [uid for uid in participant_ids if uid != actor_id]

        message = await self.message_repo.create(conversation_id, actor_id, content)
        conversation.updated_at = datetime.now(timezone.utc)

        for recipient_id in other_ids:
            if manager.is_viewing(str(recipient_id), str(conversation_id)):
                continue
            notification = await self.notification_repo.create(
                user_id=recipient_id,
                title="Nuevo mensaje",
                message=content[:120],
                type_=NotificationType.NEW_MESSAGE,
                conversation_id=conversation_id,
            )
            await manager.send_to_user(
                str(recipient_id),
                {"type": "notification", "data": self._notification_dict(notification)},
            )

        await self.db.commit()
        await self.db.refresh(message)

        message_payload = self._message_dict(message)
        for recipient_id in other_ids:
            await manager.send_to_user(
                str(recipient_id),
                {
                    "type": "message",
                    "conversation_id": str(conversation_id),
                    "data": message_payload,
                },
            )
            unread = await self.message_repo.unread_count(conversation_id, recipient_id)
            await manager.send_to_user(
                str(recipient_id),
                {
                    "type": "conversation_unread",
                    "conversation_id": str(conversation_id),
                    "data": {"unread_count": unread},
                },
            )
            notification_count = await self.notification_repo.count_unread(recipient_id)
            await manager.send_to_user(
                str(recipient_id),
                {
                    "type": "notification_count",
                    "data": {"unread_count": notification_count},
                },
            )

        return message_payload

    async def list_messages(
        self, conversation_id: UUID, user_id: UUID, page: int, page_size: int
    ) -> dict:
        if not await self.conversation_repo.is_participant(conversation_id, user_id):
            raise ForbiddenException("No eres participante de esta conversación.")

        offset = (page - 1) * page_size
        messages = await self.message_repo.list_by_conversation(conversation_id, offset, page_size)
        total = await self.message_repo.count(conversation_id)

        return {
            "items": [self._message_dict(msg) for msg in messages][::-1],
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": offset + len(messages) < total,
        }

    async def mark_conversation_read(self, conversation_id: UUID, user_id: UUID) -> int:
        if not await self.conversation_repo.is_participant(conversation_id, user_id):
            raise ForbiddenException("No eres participante de esta conversación.")
        message_ids = await self.message_repo.mark_conversation_read(conversation_id, user_id)
        await self.notification_repo.mark_read_for_conversation(conversation_id, user_id)
        await self.db.commit()

        if message_ids:
            for other_id in await self.conversation_repo.participant_ids(conversation_id):
                if other_id == user_id:
                    continue
                await manager.send_to_user(
                    str(other_id),
                    {
                        "type": "messages_read",
                        "conversation_id": str(conversation_id),
                        "data": {"message_ids": [str(mid) for mid in message_ids]},
                    },
                )
        notification_count = await self.notification_repo.count_unread(user_id)
        await manager.send_to_user(
            str(user_id),
            {"type": "notification_count", "data": {"unread_count": notification_count}},
        )
        return len(message_ids)

    async def delete_message(self, message_id: UUID, user_id: UUID) -> None:
        message = await self._get_message(message_id)
        if message.sender_user_id != user_id:
            raise ForbiddenException("Solo puedes eliminar tus propios mensajes.")
        await self.message_repo.soft_delete(message)
        await self.db.commit()

    async def _get_message(self, message_id: UUID) -> Message:
        message = await self.db.get(Message, message_id)
        if message is None or message.deleted_at is not None:
            raise NotFoundException("Mensaje no encontrado.")
        return message

    @staticmethod
    def _message_dict(message: Message) -> dict:
        return {
            "id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "sender_user_id": str(message.sender_user_id),
            "content": message.content,
            "is_read": message.is_read,
            "created_at": iso_datetime(message.created_at),
        }

    @staticmethod
    def _notification_dict(notification) -> dict:
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
            "created_at": iso_datetime(notification.created_at),
        }
