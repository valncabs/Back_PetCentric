from uuid import UUID

from pydantic import BaseModel


class CreateConversationRequest(BaseModel):
    """Abre (o reutiliza) una conversación directa con otro usuario.

    - Si es con un admin: inicia una conversación de soporte.
    - Si es con otro usuario: inicia un chat directo.
    """
    user_id: UUID
