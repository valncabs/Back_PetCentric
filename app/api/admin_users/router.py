from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.schemas.admin.create_admin import CreateAdminRequest
from app.schemas.admin.update_role import UpdateUserRoleRequest
from app.schemas.admin.update_status import UpdateUserStatusRequest
from app.services.admin_user_service import AdminUserService
from app.utils.pagination import PaginationParams
from app.utils.response import success_response

router = APIRouter(prefix="/admin/users", tags=["Admin - Users"])


@router.get("", dependencies=[Depends(require_permission("users.view"))])
async def list_users(
    role: str | None = None,
    is_active: bool | None = None,
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    data = await AdminUserService(db).list_users(params, role, is_active)
    return success_response(data=data, message="Usuarios obtenidos correctamente.")


@router.get("/{user_id}", dependencies=[Depends(require_permission("users.view"))])
async def get_user_detail(user_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await AdminUserService(db).get_user_detail(user_id)
    return success_response(data=data, message="Usuario obtenido correctamente.")


@router.patch("/{user_id}/role", dependencies=[Depends(require_permission("users.update"))])
async def update_user_role(
    user_id: UUID,
    payload: UpdateUserRoleRequest,
    db: AsyncSession = Depends(get_db),
):
    data = await AdminUserService(db).update_role(user_id, payload.role)
    return success_response(data=data, message="Rol actualizado correctamente.")


@router.patch("/{user_id}/status", dependencies=[Depends(require_permission("users.update"))])
async def update_user_status(
    user_id: UUID,
    payload: UpdateUserStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    data = await AdminUserService(db).update_status(user_id, payload.is_active)
    return success_response(data=data, message="Estado actualizado correctamente.")


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("users.create"))])
async def create_admin_user(payload: CreateAdminRequest, db: AsyncSession = Depends(get_db)):
    data = await AdminUserService(db).create_admin(payload.model_dump())
    return success_response(data=data, message="Administrador creado correctamente.", status_code=201)