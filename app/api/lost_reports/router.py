from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permission
from app.models.enums import ImageEntityType, LostReportStatus
from app.models.user import User
from app.schemas.lost_reports.create import CreateLostReportRequest
from app.schemas.lost_reports.update import UpdateLostReportRequest
from app.services.image_service import ImageService
from app.services.lost_report_service import LostReportService
from app.utils.pagination import PaginationParams
from app.utils.response import success_response

router = APIRouter(prefix="/lost-reports", tags=["Lost Reports"])


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("lost_reports.create"))])
async def create_lost_report(
    payload: CreateLostReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await LostReportService(db).create_report(current_user.id, payload.model_dump())
    return success_response(data=data, message="Reporte de mascota perdida creado.", status_code=201)


@router.get("")
async def list_lost_reports(
    status_filter: LostReportStatus | None = None,
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    data = await LostReportService(db).list_reports(params, status_filter)
    return success_response(data=data, message="Reportes obtenidos correctamente.")


@router.get("/{report_id}")
async def get_lost_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await LostReportService(db).get_report(report_id)
    return success_response(data=data, message="Reporte obtenido correctamente.")


@router.patch("/{report_id}", dependencies=[Depends(require_permission("lost_reports.update"))])
async def update_lost_report(
    report_id: UUID,
    payload: UpdateLostReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await LostReportService(db).update_report(report_id, current_user.id, payload.model_dump())
    return success_response(data=data, message="Reporte actualizado correctamente.")


@router.post("/{report_id}/mark-as-found", dependencies=[Depends(require_permission("lost_reports.update"))])
async def mark_lost_report_as_found(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await LostReportService(db).mark_as_found(report_id, current_user.id)
    return success_response(data=data, message="Reporte marcado como encontrado.")


@router.post("/{report_id}/close", dependencies=[Depends(require_permission("lost_reports.close"))])
async def close_lost_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await LostReportService(db).close_report(report_id, current_user.id)
    return success_response(data=data, message="Reporte cerrado correctamente.")


# ---------- Imágenes del reporte ----------

@router.post("/{report_id}/images", status_code=status.HTTP_201_CREATED)
async def upload_lost_report_image(
    report_id: UUID,
    file: UploadFile = File(...),
    is_primary: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verifica ownership antes de delegar al service genérico de imágenes.
    await LostReportService(db)._get_owned_report(report_id, current_user.id)
    data = await ImageService(db).upload(
        ImageEntityType.LOST_REPORT, report_id, current_user.id, file, is_primary
    )
    return success_response(data=data, message="Imagen subida correctamente.", status_code=201)


@router.get("/{report_id}/images")
async def list_lost_report_images(report_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await ImageService(db).list_for_entity(ImageEntityType.LOST_REPORT, report_id)
    return success_response(data=data, message="Imágenes obtenidas correctamente.")


@router.delete("/{report_id}/images/{image_id}")
async def delete_lost_report_image(
    report_id: UUID,
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await LostReportService(db)._get_owned_report(report_id, current_user.id)
    await ImageService(db).delete(image_id, ImageEntityType.LOST_REPORT, report_id)
    return success_response(message="Imagen eliminada correctamente.")