from fastapi import APIRouter, Depends

from app.schemas.chat.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/ask", tags=["Chat IA"])


@router.post("", response_model=ChatResponse)
async def ask_chat(payload: ChatRequest) -> ChatResponse:
    return await ChatService().ask(payload.question)