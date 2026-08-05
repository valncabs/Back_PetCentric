from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.communication import Conversation, ConversationParticipant


class ConversationRepository:
    """Acceso a datos de conversaciones. No decide transacciones: el Service
    controla cuándo hacer commit."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_participants(self, conversation_id: UUID) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.participants).selectinload(
                    ConversationParticipant.user
                )
            )
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_direct_between(self, user_a: UUID, user_b: UUID) -> Conversation | None:
        """Conversación directa (exactamente 2 participantes) entre dos usuarios,
        si ya existe. El UNIQUE(conversation_id, user_id) no garantiza unicidad
        de la pareja, así que se verifica que no haya terceros."""
        first = select(ConversationParticipant.conversation_id).where(
            ConversationParticipant.user_id == user_a
        )
        stmt = (
            select(ConversationParticipant.conversation_id)
            .where(
                ConversationParticipant.conversation_id.in_(first),
                ConversationParticipant.user_id == user_b,
            )
        )
        candidate_ids = list((await self.db.execute(stmt)).scalars().all())

        for conversation_id in candidate_ids:
            participant_ids = await self._participant_ids(conversation_id)
            if set(participant_ids) == {user_a, user_b}:
                return await self.get_by_id_with_participants(conversation_id)
        return None

    async def get_or_create_direct(self, user_a: UUID, user_b: UUID) -> Conversation:
        existing = await self.get_direct_between(user_a, user_b)
        if existing is not None:
            return existing

        conversation = Conversation()
        self.db.add(conversation)
        await self.db.flush()

        self.db.add(
            ConversationParticipant(conversation_id=conversation.id, user_id=user_a)
        )
        self.db.add(
            ConversationParticipant(conversation_id=conversation.id, user_id=user_b)
        )
        await self.db.flush()
        return await self.get_by_id_with_participants(conversation.id)

    async def list_for_user(self, user_id: UUID) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.id,
            )
            .where(ConversationParticipant.user_id == user_id)
            .options(
                selectinload(Conversation.participants).selectinload(
                    ConversationParticipant.user
                )
            )
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().unique().all())

    async def is_participant(self, conversation_id: UUID, user_id: UUID) -> bool:
        result = await self.db.execute(
            select(ConversationParticipant.id).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def participant_ids(self, conversation_id: UUID) -> list[UUID]:
        return await self._participant_ids(conversation_id)

    async def _participant_ids(self, conversation_id: UUID) -> list[UUID]:
        result = await self.db.execute(
            select(ConversationParticipant.user_id).where(
                ConversationParticipant.conversation_id == conversation_id
            )
        )
        return list(result.scalars().all())
