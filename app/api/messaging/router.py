from uuid import UUID

import json

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.security import decode_token
from app.dependencies.auth import get_current_user
from app.dependencies.profile import require_completed_profile_or_admin
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.messaging import CreateConversationRequest, SendMessageRequest
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.utils.response import success_response
from app.websocket import manager

router = APIRouter(tags=["Messaging"])


# ---------- Conversaciones ----------

@router.post("/conversations/support", status_code=status.HTTP_201_CREATED)
async def open_support_conversation(
    current_user: User = Depends(require_completed_profile_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Abre una conversación con un miembro del equipo de soporte."""
    data = await ConversationService(db).open_support_conversation(current_user.id)
    return success_response(data=data, message="Conversación de soporte abierta.", status_code=201)


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def open_direct_conversation(
    payload: CreateConversationRequest,
    current_user: User = Depends(require_completed_profile_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Abre (o reutiliza) una conversación directa con otro usuario."""
    data = await ConversationService(db).open_direct_conversation(current_user.id, payload.user_id)
    return success_response(data=data, message="Conversación creada correctamente.", status_code=201)


@router.get("/conversations")
async def list_my_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await ConversationService(db).list_mine(current_user.id)
    return success_response(data=data, message="Conversaciones obtenidas correctamente.")


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await ConversationService(db).get_conversation(conversation_id, current_user.id)
    return success_response(data=data, message="Conversación obtenida correctamente.")


@router.post("/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    marked = await MessageService(db).mark_conversation_read(conversation_id, current_user.id)
    return success_response(data={"marked": marked}, message="Mensajes marcados como leídos.")


@router.get("/conversations/{conversation_id}/messages")
async def list_conversation_messages(
    conversation_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await MessageService(db).list_messages(conversation_id, current_user.id, page, page_size)
    return success_response(data=data, message="Mensajes obtenidos correctamente.")


# ---------- Mensajes ----------

@router.post("/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    payload: SendMessageRequest,
    current_user: User = Depends(require_completed_profile_or_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await MessageService(db).send_message(current_user.id, payload.conversation_id, payload.content)
    return success_response(data=data, message="Mensaje enviado correctamente.", status_code=201)


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: UUID,
    current_user: User = Depends(require_completed_profile_or_admin),
    db: AsyncSession = Depends(get_db),
):
    await MessageService(db).delete_message(message_id, current_user.id)
    return success_response(message="Mensaje eliminado correctamente.")


# ---------- Tiempo real ----------

@router.websocket("/ws/messages")
async def websocket_messages(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = decode_token(token)
    except ValueError as exc:
        await websocket.close(code=4401)
        return
    if payload.get("type") != "access":
        await websocket.close(code=4401)
        return

    user_id = payload.get("sub")
    try:
        user_uuid = UUID(user_id)
    except (ValueError, TypeError):
        await websocket.close(code=4401)
        return

    async with AsyncSessionLocal() as db:
        user = await UserRepository(db).get_by_id(user_uuid)
        if user is None or not user.is_active:
            await websocket.close(code=4401)
            return

        await manager.connect(str(user_uuid), websocket)
        try:
            while True:
                raw = await websocket.receive_text()
                if not raw:
                    continue
                try:
                    msg = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    continue
                if msg.get("type") == "viewing":
                    manager.set_viewing(
                        str(user_uuid), websocket, msg.get("conversation_id")
                    )
        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(str(user_uuid), websocket)
