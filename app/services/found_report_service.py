from datetime import datetime, timezone
from uuid import UUID
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.enums import FoundReportStatus
from app.models.report import FoundReport
from app.repositories.found_report_repository import FoundReportRepository
from app.utils.pagination import PaginationParams, paginate


class FoundReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.report_repo = FoundReportRepository(db)

    async def create_report(self, user_id: UUID, data: dict[str, Any]) -> dict:
        report = await self.report_repo.create(user_id, data)
        await self.db.commit()
        return self._to_dict(report)

    async def get_report(self, report_id: UUID) -> dict:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        return self._to_dict(report)

    async def list_reports(self, params: PaginationParams, status: FoundReportStatus | None = None) -> dict:
        stmt = self.report_repo.base_query(params.search, status, params.sort, params.order)
        return await paginate(self.db, stmt, params, self._to_list_item)

    async def update_report(self, report_id: UUID, user_id: UUID, data: dict[str, Any]) -> dict:
        report = await self.verify_ownership(report_id, user_id)
        if report.status != FoundReportStatus.PUBLISHED:
            raise BadRequestException("Solo se puede editar un reporte mientras está publicado.")

        update_data = {field: value for field, value in data.items() if value is not None}
        report = await self.report_repo.update(report, update_data)
        await self.db.commit()
        return self._to_dict(report)

    async def approve_report(self, report_id: UUID, admin_user_id: UUID) -> dict:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        if report.status != FoundReportStatus.PUBLISHED:
            raise BadRequestException("Solo un reporte publicado puede aprobarse.")

        report.status = FoundReportStatus.APPROVED
        report.approved_by = admin_user_id
        report.approved_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(report)
        return self._to_dict(report)

    async def reject_report(self, report_id: UUID, admin_user_id: UUID) -> dict:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        if report.status != FoundReportStatus.PUBLISHED:
            raise BadRequestException("Solo un reporte publicado puede rechazarse.")

        report.status = FoundReportStatus.REJECTED
        report.approved_by = admin_user_id
        report.approved_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(report)
        return self._to_dict(report)

    async def close_report(self, report_id: UUID, user_id: UUID) -> dict:
        report = await self.verify_ownership(report_id, user_id)
        if report.status == FoundReportStatus.CLOSED:
            raise BadRequestException("El reporte ya está cerrado.")

        report.status = FoundReportStatus.CLOSED
        report.closed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(report)
        return self._to_dict(report)

    async def verify_ownership(self, report_id: UUID, user_id: UUID) -> FoundReport:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        if report.created_by != user_id:
            raise ForbiddenException("No tienes permiso sobre este reporte.")
        return report

    @staticmethod
    def _to_dict(report: FoundReport) -> dict:
        return {
            "id": str(report.id),
            "created_by": str(report.created_by),
            "title": report.title,
            "description": report.description,
            "status": report.status,
            "found_date": report.found_date,
            "contact_phone": report.contact_phone,
            "country": report.country,
            "department": report.department,
            "city": report.city,
            "address": report.address,
            "approved_by": str(report.approved_by) if report.approved_by else None,
            "approved_at": report.approved_at,
            "published_at": report.published_at,
            "closed_at": report.closed_at,
        }

    @staticmethod
    def _to_list_item(report: FoundReport) -> dict:
        return {
            "id": str(report.id),
            "title": report.title,
            "status": report.status,
            "city": report.city,
            "found_date": report.found_date,
            "published_at": report.published_at,
        }