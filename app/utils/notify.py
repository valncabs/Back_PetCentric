from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Role, UserRole
from app.models.enums import NotificationType
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.notification_repository import NotificationRepository
from app.utils.serializers import iso_datetime
from app.websocket import manager


async def admin_user_ids(db: AsyncSession) -> list[UUID]:
    """Ids de todos los admins activos (no borrados). Se usan para avisar al
    equipo cuando un dueño solicita marcar su mascota como encontrada o
    confirma un encuentro, porque el admin es quien aprueba el cambio."""
    result = await db.execute(
        select(User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            Role.name == "ADMIN",
            Role.is_active.is_(True),
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def notify_user(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    message: str,
    type_: NotificationType,
    conversation_id: UUID | None = None,
    lost_report_id: UUID | None = None,
) -> None:
    """Crea una notificación y la entrega en tiempo real por WebSocket."""
    repo = NotificationRepository(db)
    notification = await repo.create(user_id, title, message, type_, conversation_id, lost_report_id)
    await manager.send_to_user(
        str(user_id),
        {"type": "notification", "data": _notification_dict(notification)},
    )
    unread = await repo.count_unread(user_id)
    await manager.send_to_user(
        str(user_id),
        {"type": "notification_count", "data": {"unread_count": unread}},
    )


async def send_message_inline(
    db: AsyncSession,
    sender_id: UUID,
    conversation_id: UUID,
    content: str,
) -> None:
    """Envía un mensaje dentro de una transacción YA abierta (sin commit
    propio, el llamador controla el commit). Reproduce la misma lógica de
    MessageService.send_message pero sin cerrar la transacción."""
    conversation_repo = ConversationRepository(db)
    message_repo = MessageRepository(db)
    notification_repo = NotificationRepository(db)

    if not await conversation_repo.is_participant(conversation_id, sender_id):
        return

    conversation = await conversation_repo.get_by_id(conversation_id)
    if conversation is None:
        return

    participant_ids = await conversation_repo.participant_ids(conversation_id)
    other_ids = [uid for uid in participant_ids if uid != sender_id]

    message = await message_repo.create(conversation_id, sender_id, content)
    conversation.updated_at = datetime.now(timezone.utc)

    for recipient_id in other_ids:
        if manager.is_viewing(str(recipient_id), str(conversation_id)):
            continue
        notification = await notification_repo.create(
            user_id=recipient_id,
            title="Nuevo mensaje",
            message=content[:120],
            type_=NotificationType.NEW_MESSAGE,
            conversation_id=conversation_id,
        )
        await manager.send_to_user(
            str(recipient_id),
            {"type": "notification", "data": _notification_dict(notification)},
        )

    message_payload = _message_dict(message)
    for recipient_id in other_ids:
        await manager.send_to_user(
            str(recipient_id),
            {
                "type": "message",
                "conversation_id": str(conversation_id),
                "data": message_payload,
            },
        )
        unread = await message_repo.unread_count(conversation_id, recipient_id)
        await manager.send_to_user(
            str(recipient_id),
            {
                "type": "conversation_unread",
                "conversation_id": str(conversation_id),
                "data": {"unread_count": unread},
            },
        )
        notification_count = await notification_repo.count_unread(recipient_id)
        await manager.send_to_user(
            str(recipient_id),
            {"type": "notification_count", "data": {"unread_count": notification_count}},
        )


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
        "lost_report_id": (
            str(notification.lost_report_id)
            if notification.lost_report_id is not None
            else None
        ),
        "created_at": iso_datetime(notification.created_at),
    }


def _message_dict(message) -> dict:
    return {
        "id": str(message.id),
        "conversation_id": str(message.conversation_id),
        "sender_user_id": str(message.sender_user_id),
        "content": message.content,
        "is_read": message.is_read,
        "created_at": iso_datetime(message.created_at),
    }
