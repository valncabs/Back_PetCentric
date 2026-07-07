from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.profile.create_profile import CreateProfileRequest
from app.schemas.profile.update_profile import UpdateProfileRequest
from app.services.profile_service import ProfileService
from app.utils.response import success_response

router = APIRouter(prefix="/users/me/profile", tags=["Profile"])


@router.get("")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await ProfileService(db).get_profile(current_user.id)
    return success_response(data=data, message="Perfil obtenido correctamente.")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    payload: CreateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await ProfileService(db).create_profile(current_user.id, payload.model_dump())
    return success_response(data=data, message="Perfil creado correctamente.", status_code=201)


@router.patch("")
async def update_my_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await ProfileService(db).update_profile(current_user.id, payload.model_dump())
    return success_response(data=data, message="Perfil actualizado correctamente.")