from uuid import UUID

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
_log = logging.getLogger(__name__)


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

async def _read_frame(websocket: WebSocket) -> tuple[str | None, int | None]:
    """Lee un frame con límite de tamaño y timeout de keepalive.

    Devuelve (raw, close_code): si el frame supera el tamaño máximo se
    devuelve close_code=1009; si hay timeout de keepalive se devuelve
    (None, None) para que el llamador envíe el ping."""
    raw = await asyncio.wait_for(
        websocket.receive_text(), timeout=settings.WS_PING_INTERVAL_SECONDS
    )
    if len(raw) > settings.WS_MAX_MESSAGE_BYTES:
        return None, 1009
    return raw, None


@router.websocket("/ws/messages")
async def websocket_messages(websocket: WebSocket):
    await websocket.accept()

    # Autenticación por primer mensaje en vez de query param: el token nunca
    # viaja en la URL (evita fugas por logs/proxies).
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
    except (asyncio.TimeoutError, WebSocketDisconnect):
        _log.warning("WS auth: timeout esperando token (ip=%s)", websocket.client.host)
        await websocket.close(code=4401)
        return

    if len(auth_msg) > settings.WS_MAX_MESSAGE_BYTES:
        await websocket.close(code=1009)
        return

    try:
        auth_payload = json.loads(auth_msg)
        raw_token = auth_payload.get("token") if isinstance(auth_payload, dict) else None
    except (json.JSONDecodeError, ValueError):
        raw_token = None

    if not raw_token:
        _log.warning("WS auth: sin token (ip=%s)", websocket.client.host)
        await websocket.close(code=4401)
        return

    try:
        payload = decode_token(raw_token)
    except ValueError:
        _log.warning("WS auth: token inválido (ip=%s)", websocket.client.host)
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
            _log.warning("WS auth: usuario inexistente o inactivo (user=%s)", user_id)
            await websocket.close(code=4401)
            return
        # Tokens emitidos antes de un cambio de contraseña son inválidos.
        if payload.get("ver") is None or payload.get("ver") != user.token_version:
            _log.warning("WS auth: token de sesión vieja (user=%s)", user_id)
            await websocket.close(code=4401)
            return

        await manager.connect(str(user_uuid), websocket)
        _log.info("WS conectado: user=%s ip=%s", user_uuid, websocket.client.host)
        try:
            while True:
                try:
                    raw, close_code = await _read_frame(websocket)
                except asyncio.TimeoutError:
                    # Keepalive: si el cliente está muerto, el send falla y se
                    # limpia; si vive, el navegador responde (protocolo) y el
                    # cliente además responde {"type":"pong"}.
                    await websocket.send_text(json.dumps({"type": "ping"}))
                    continue

                if close_code is not None:
                    _log.info("WS cerrado por exceso de tamaño: user=%s", user_uuid)
                    await websocket.close(code=close_code)
                    break
                if not raw:
                    continue

                try:
                    msg = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    continue

                if not isinstance(msg, dict):
                    continue
                if msg.get("type") == "viewing":
                    manager.set_viewing(
                        str(user_uuid), websocket, msg.get("conversation_id")
                    )
        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(str(user_uuid), websocket)
            _log.info("WS desconectado: user=%s", user_uuid)
