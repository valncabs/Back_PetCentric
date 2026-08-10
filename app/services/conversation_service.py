from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.auth import Role, UserRole
from app.models.communication import Conversation
from app.models.enums import ImageEntityType
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.image_repository import ImageRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.user import UserRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.utils.serializers import iso_datetime


class ConversationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        self.user_repo = UserRepository(db)
        self.profile_repo = UserProfileRepository(db)
        self.image_repo = ImageRepository(db)

    # ---------- Soporte (con un admin) ----------

    async def open_support_conversation(self, user_id: UUID) -> dict:
        """Busca un admin disponible y abre (o reutiliza) una conversación
        con él. El usuario de la plataforma solo ve 'Equipo Pet-Centric'."""
        admin = await self._find_any_admin()
        if admin is None:
            raise BadRequestException(
                "No hay un miembro del equipo disponible para soporte. Intenta más tarde."
            )
        conversation = await self.conversation_repo.get_or_create_direct(user_id, admin.id)
        await self.db.commit()
        conversation = await self.conversation_repo.get_by_id_with_participants(conversation.id)
        return await self._build_conversation(conversation, user_id)

    # ---------- Chat directo ----------

    async def open_direct_conversation(self, actor_id: UUID, other_user_id: UUID) -> dict:
        if actor_id == other_user_id:
            raise BadRequestException("No puedes iniciar una conversación contigo mismo.")

        other = await self.user_repo.get_by_id(other_user_id)
        if other is None:
            raise NotFoundException("El usuario con el que quieres hablar no existe.")

        conversation = await self.conversation_repo.get_or_create_direct(actor_id, other_user_id)
        await self.db.commit()
        conversation = await self.conversation_repo.get_by_id_with_participants(conversation.id)
        return await self._build_conversation(conversation, actor_id)

    # ---------- Listado ----------

    async def list_mine(self, user_id: UUID) -> list[dict]:
        conversations = await self.conversation_repo.list_for_user(user_id)
        if not conversations:
            return []

        # Cargar en bloque los datos de TODAS las conversaciones (evita N+1):
        # perfiles, fotos, último mensaje y no leídos se resuelven con 4 queries.
        other_by_conversation: dict[UUID, User] = {}
        other_ids: list[UUID] = []
        for conversation in conversations:
            participants = [
                p for p in conversation.participants if p.user_id != user_id
            ]
            if participants:
                other = participants[0].user
                other_by_conversation[conversation.id] = other
                other_ids.append(other.id)

        unique_other_ids = list(dict.fromkeys(other_ids))
        conversation_ids = [c.id for c in conversations]

        profiles = await self.profile_repo.get_by_user_ids(unique_other_ids)
        images = await self.image_repo.list_by_entities(
            ImageEntityType.USER_PROFILE, unique_other_ids
        )
        last_messages = await self.message_repo.last_messages(conversation_ids)
        unread_counts = await self.message_repo.unread_counts(conversation_ids, user_id)

        items = []
        for conversation in conversations:
            other = other_by_conversation.get(conversation.id)
            last_message = last_messages.get(conversation.id)
            unread = unread_counts.get(conversation.id, 0)
            participant = None
            if other is not None:
                participant = self._user_public_dict_loaded(
                    other,
                    profiles.get(other.id),
                    images.get(other.id, []),
                )
            items.append(
                {
                    "id": str(conversation.id),
                    "participant": participant,
                    "last_message": (
                        self._message_dict(last_message) if last_message else None
                    ),
                    "unread_count": unread,
                    "created_at": iso_datetime(conversation.created_at),
                    "updated_at": iso_datetime(conversation.updated_at),
                }
            )
        return items

    async def get_conversation(self, conversation_id: UUID, user_id: UUID) -> dict:
        conversation = await self.conversation_repo.get_by_id_with_participants(conversation_id)
        if conversation is None:
            raise NotFoundException("Conversación no encontrada.")
        if not await self.conversation_repo.is_participant(conversation_id, user_id):
            raise BadRequestException("No eres participante de esta conversación.")
        return await self._build_conversation(conversation, user_id)

    # ---------- Construcción de respuesta ----------

    async def _build_conversation(self, conversation: Conversation, viewer_id: UUID) -> dict:
        participants = [
            p for p in conversation.participants if p.user_id != viewer_id
        ]
        other = participants[0].user if participants else None
        last_message = await self.message_repo.last_message(conversation.id)
        unread = await self.message_repo.unread_count(conversation.id, viewer_id)

        return {
            "id": str(conversation.id),
            "participant": await self._user_public_dict(other) if other else None,
            "last_message": self._message_dict(last_message) if last_message else None,
            "unread_count": unread,
            "created_at": iso_datetime(conversation.created_at),
            "updated_at": iso_datetime(conversation.updated_at),
        }

    async def _user_public_dict(self, user: User) -> dict:
        profile = await self.profile_repo.get_by_user_id(user.id)
        images = await self.image_repo.list_by_entity(ImageEntityType.USER_PROFILE, user.id)
        return self._user_public_dict_loaded(user, profile, images)

    @staticmethod
    def _user_public_dict_loaded(
        user: User, profile, images: list
    ) -> dict:
        """Construye el dict del participante a partir de datos ya cargados
        (evita re-consultar perfil/foto en listados)."""
        full_name = None
        if profile:
            full_name = f"{profile.first_name} {profile.last_name}".strip()

        photo_url = None
        if images:
            primary = next((img for img in images if img.is_primary), images[0])
            photo_url = primary.file_path

        return {
            "id": str(user.id),
            "full_name": full_name or user.email,
            "email": user.email,
            "photo_url": photo_url,
        }

    @staticmethod
    def _message_dict(message) -> dict:
        return {
            "id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "sender_user_id": str(message.sender_user_id),
            "content": message.content,
            "is_read": message.is_read,
            "created_at": iso_datetime(message.created_at),
        }

    # ---------- Internos ----------

    async def _find_any_admin(self) -> User | None:
        stmt = (
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                Role.name == "ADMIN",
                Role.is_active.is_(True),
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
            .order_by(User.created_at.asc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
