import asyncio
import json

from fastapi import WebSocket


class ConnectionManager:
    """Mantiene los sockets abiertos por usuario (str(user_id)).

    Un usuario puede tener varios sockets abiertos (pestañas/dispositivos):
    `send_to_user` entrega el evento a todos ellos.

    Además se rastrea qué conversación está viendo cada socket (estado
    `viewing`) para no crear notificaciones cuando el destinatario ya tiene
    el chat abierto.
    """

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._viewing: dict[str, dict[WebSocket, str | None]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(user_id, set()).add(websocket)
            self._viewing.setdefault(user_id, {})[websocket] = None

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._connections.get(user_id)
            if sockets:
                sockets.discard(websocket)
                if not sockets:
                    self._connections.pop(user_id, None)
            viewing = self._viewing.get(user_id)
            if viewing:
                viewing.pop(websocket, None)
                if not viewing:
                    self._viewing.pop(user_id, None)

    def set_viewing(self, user_id: str, websocket: WebSocket, conversation_id: str | None) -> None:
        viewing = self._viewing.get(user_id)
        if viewing is not None:
            viewing[websocket] = conversation_id

    def is_viewing(self, user_id: str, conversation_id: str) -> bool:
        viewing = self._viewing.get(user_id)
        if not viewing:
            return False
        return conversation_id in viewing.values()

    async def send_to_user(self, user_id: str, event: dict) -> None:
        sockets = list(self._connections.get(user_id, set()))
        if not sockets:
            return
        payload = json.dumps(event, default=str, ensure_ascii=False)
        for websocket in sockets:
            try:
                await websocket.send_text(payload)
            except Exception:
                await self.disconnect(user_id, websocket)


manager = ConnectionManager()
