from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.services.admin_report_service import AdminReportService
from app.utils.response import success_response

router = APIRouter(prefix="/admin/reports", tags=["Admin - Reports"])


@router.get("", dependencies=[Depends(require_permission("reports.view"))])
async def list_admin_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),  # antes: le=100
    search: str | None = None,
    report_type: str | None = Query(None, pattern="^(LOST|FOUND)$"),
    species_id: UUID | None = None,
    status: str | None = None,
    city: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    data = await AdminReportService(db).list_all_reports(
        page, page_size, search, report_type, species_id, status, city, date_from, date_to
    )
    return success_response(data=data, message="Reportes obtenidos correctamente.")