from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permission
from app.models.enums import FoundReportStatus, ImageEntityType
from app.models.user import User
from app.schemas.found_reports.create import CreateFoundReportRequest
from app.services.found_report_service import FoundReportService
from app.services.image_service import ImageService
from app.utils.pagination import PaginationParams
from app.utils.response import success_response
from app.schemas.found_reports.update import UpdateFoundReportRequest

router = APIRouter(prefix="/found-reports", tags=["Found Reports"])


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("found_reports.create"))])
async def create_found_report(
    payload: CreateFoundReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await FoundReportService(db).create_report(current_user.id, payload.model_dump())
    return success_response(data=data, message="Reporte de mascota encontrada creado.", status_code=201)


@router.get("/mine")
async def list_my_found_reports(
    params: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await FoundReportService(db).list_my_reports(current_user.id, params)
    return success_response(data=data, message="Tus reportes obtenidos correctamente.")


@router.get("")
async def list_found_reports(
    status_filter: FoundReportStatus | None = None,
    species_id: UUID | None = None,
    city: str | None = None,
    lost_report_id: UUID | None = None,
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    data = await FoundReportService(db).list_reports(
        params, status_filter, species_id, city, lost_report_id=lost_report_id
    )
    return success_response(data=data, message="Reportes obtenidos correctamente.")


@router.get("/by-lost-report/{lost_report_id}")
async def list_sightings_for_lost_report(lost_report_id: UUID, db: AsyncSession = Depends(get_db)):
    """Todos los avistamientos asociados a un reporte de pérdida, sin
    paginar (se usa en el detalle de 'Mis reportes')."""
    data = await FoundReportService(db).list_by_lost_report(lost_report_id)
    return success_response(data=data, message="Avistamientos obtenidos correctamente.")


@router.get("/{report_id}")
async def get_found_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await FoundReportService(db).get_report(report_id)
    return success_response(data=data, message="Reporte obtenido correctamente.")


# ---------- Flujo de coincidencia (dueño del lost_report asociado) ----------

@router.post("/{report_id}/match")
async def match_found_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await FoundReportService(db).match_report(report_id, current_user.id)
    return success_response(data=data, message="Avistamiento marcado como coincidencia.")


@router.post("/{report_id}/unmatch")
async def unmatch_found_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await FoundReportService(db).unmatch_report(report_id, current_user.id)
    return success_response(data=data, message="Coincidencia descartada.")


@router.post("/{report_id}/confirm-found")
async def confirm_found_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await FoundReportService(db).confirm_found(report_id, current_user.id)
    return success_response(data=data, message="Encuentro confirmado. Pendiente de aprobación final.")


# ---------- Aprobación / rechazo (admin) ----------

@router.post("/{report_id}/approve", dependencies=[Depends(require_permission("found_reports.approve"))])
async def approve_found_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await FoundReportService(db).approve_report(report_id, current_user.id)
    return success_response(data=data, message="Reporte aprobado correctamente.")


@router.post("/{report_id}/reject", dependencies=[Depends(require_permission("found_reports.reject"))])
async def reject_found_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await FoundReportService(db).reject_report(report_id, current_user.id)
    return success_response(data=data, message="Reporte rechazado correctamente.")


@router.post("/{report_id}/close", dependencies=[Depends(require_permission("found_reports.close"))])
async def close_found_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await FoundReportService(db).close_report(report_id, current_user.id)
    return success_response(data=data, message="Reporte cerrado correctamente.")


# ---------- Imágenes del reporte ----------

@router.post("/{report_id}/images", status_code=status.HTTP_201_CREATED)
async def upload_found_report_image(
    report_id: UUID,
    file: UploadFile = File(...),
    is_primary: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FoundReportService(db).verify_ownership(report_id, current_user.id)
    data = await ImageService(db).upload(
        ImageEntityType.FOUND_REPORT, report_id, current_user.id, file, is_primary
    )
    return success_response(data=data, message="Imagen subida correctamente.", status_code=201)


@router.get("/{report_id}/images")
async def list_found_report_images(report_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await ImageService(db).list_for_entity(ImageEntityType.FOUND_REPORT, report_id)
    return success_response(data=data, message="Imágenes obtenidas correctamente.")


@router.delete("/{report_id}/images/{image_id}")
async def delete_found_report_image(
    report_id: UUID,
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FoundReportService(db).verify_ownership(report_id, current_user.id)
    await ImageService(db).delete(image_id, ImageEntityType.FOUND_REPORT, report_id)
    return success_response(message="Imagen eliminada correctamente.")

@router.patch("/{report_id}")
async def update_found_report(
    report_id: UUID,
    payload: UpdateFoundReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await FoundReportService(db).update_report(report_id, current_user.id, payload.model_dump())
    return success_response(data=data, message="Reporte actualizado correctamente.")


@router.delete("/{report_id}")
async def delete_found_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FoundReportService(db).delete_report(report_id, current_user.id)
    return success_response(message="Reporte eliminado correctamente.")

@router.get("")
async def list_found_reports(
    status_filter: FoundReportStatus | None = None,
    species_id: UUID | None = None,
    city: str | None = None,
    lost_report_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    data = await FoundReportService(db).list_reports(
        params, status_filter, species_id, city, lost_report_id=lost_report_id,
        date_from=date_from, date_to=date_to
    )
    return success_response(data=data, message="Reportes obtenidos correctamente.")


# nuevas rutas admin, al final del archivo:
@router.post("/{report_id}/admin-close", dependencies=[Depends(require_permission("found_reports.admin_manage"))])
async def admin_close_found_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await FoundReportService(db).admin_close_report(report_id)
    return success_response(data=data, message="Reporte cerrado por administrador.")


@router.delete("/{report_id}/admin-delete", dependencies=[Depends(require_permission("found_reports.admin_manage"))])
async def admin_delete_found_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    await FoundReportService(db).admin_delete_report(report_id)
    return success_response(message="Reporte eliminado por administrador.")