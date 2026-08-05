from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService
from app.utils.response import success_response

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_my_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await NotificationService(db).list_mine(current_user.id, page, page_size)
    return success_response(data=data, message="Notificaciones obtenidas correctamente.")


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await NotificationService(db).unread_count(current_user.id)
    return success_response(data={"unread_count": data}, message="Contador de no leídas obtenido.")


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await NotificationService(db).mark_read(notification_id, current_user.id)
    return success_response(data=data, message="Notificación marcada como leída.")


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await NotificationService(db).mark_all_read(current_user.id)
    return success_response(message="Todas las notificaciones fueron marcadas como leídas.")
