import secrets

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import ForbiddenException
from app.schemas.chat.chat import ChatRequest, ChatResponse, ProxyUrlUpdate
from app.services.chat_service import ChatService
from app.services.proxy_registry import update_proxy_url
from app.utils.response import success_response

router = APIRouter(prefix="/ask", tags=["Chat IA"])


@router.post("", response_model=ChatResponse)
async def ask_chat(payload: ChatRequest) -> ChatResponse:
    return await ChatService().ask(payload.question)


@router.post("/internal/proxy-url")
async def update_runtime_proxy_url(
    payload: ProxyUrlUpdate,
    x_proxy_key: str | None = Header(default=None, alias="X-Proxy-Key"),
) -> JSONResponse:
    """Actualiza en tiempo de ejecución la URL del proxy de herramientas.

    Protegido por la clave compartida AI_TOOL_PROXY_KEY enviada en el header
    X-Proxy-Key. Lo usa iniciar.sh para registrar el quick tunnel de cloudflared.
    """
    if not settings.AI_TOOL_PROXY_KEY:
        raise ForbiddenException(
            "AI_TOOL_PROXY_KEY no está configurada en el backend; no se aceptan cambios."
        )
    if not x_proxy_key or not secrets.compare_digest(
        x_proxy_key, settings.AI_TOOL_PROXY_KEY
    ):
        raise ForbiddenException("X-Proxy-Key incorrecta o faltante.")

    effective = await update_proxy_url(payload.proxy_url)
    return success_response(
        data={"proxy_url": effective},
        message="URL del proxy de herramientas actualizada.",
    )