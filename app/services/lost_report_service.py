from datetime import datetime, timezone
from uuid import UUID
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.enums import LostReportStatus
from app.models.report import LostReport
from app.repositories.lost_report_repository import LostReportRepository
from app.repositories.pet_repository import PetRepository
from app.utils.pagination import PaginationParams, paginate


class LostReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.report_repo = LostReportRepository(db)
        self.pet_repo = PetRepository(db)

    async def create_report(self, user_id: UUID, data: dict[str, Any]) -> dict:
        pet = await self.pet_repo.get_by_id_for_owner(data["pet_id"], user_id)
        if pet is None:
            raise NotFoundException(
                "La mascota indicada no existe o no te pertenece.",
                errors={"pet_id": ["Mascota no encontrada."]},
            )

        report = await self.report_repo.create(user_id, data)
        await self.db.commit()
        return self._to_dict(report)

    async def get_report(self, report_id: UUID) -> dict:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        return self._to_dict(report)

    async def list_reports(self, params: PaginationParams, status: LostReportStatus | None = None) -> dict:
        stmt = self.report_repo.base_query(params.search, status, params.sort, params.order)
        return await paginate(self.db, stmt, params, self._to_list_item)

    async def update_report(self, report_id: UUID, user_id: UUID, data: dict[str, Any]) -> dict:
        report = await self._get_owned_editable_report(report_id, user_id)
        update_data = {field: value for field, value in data.items() if value is not None}
        report = await self.report_repo.update(report, update_data)
        await self.db.commit()
        return self._to_dict(report)

    async def mark_as_found(self, report_id: UUID, user_id: UUID) -> dict:
        report = await self._get_owned_report(report_id, user_id)
        if report.status != LostReportStatus.PUBLISHED:
            raise BadRequestException("Solo un reporte publicado puede marcarse como encontrado.")

        report.status = LostReportStatus.FOUND
        await self.db.commit()
        await self.db.refresh(report)
        return self._to_dict(report)

    async def close_report(self, report_id: UUID, user_id: UUID) -> dict:
        report = await self._get_owned_report(report_id, user_id)
        if report.status == LostReportStatus.CLOSED:
            raise BadRequestException("El reporte ya está cerrado.")

        report.status = LostReportStatus.CLOSED
        report.closed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(report)
        return self._to_dict(report)

    # ---------- Helpers internos ----------

    async def _get_owned_report(self, report_id: UUID, user_id: UUID) -> LostReport:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        if report.created_by != user_id:
            raise ForbiddenException("No tienes permiso sobre este reporte.")
        return report

    async def _get_owned_editable_report(self, report_id: UUID, user_id: UUID) -> LostReport:
        report = await self._get_owned_report(report_id, user_id)
        if report.status != LostReportStatus.PUBLISHED:
            raise BadRequestException("Solo se puede editar un reporte mientras está publicado.")
        return report

    @staticmethod
    def _to_dict(report: LostReport) -> dict:
        return {
            "id": str(report.id),
            "pet_id": str(report.pet_id),
            "created_by": str(report.created_by),
            "title": report.title,
            "description": report.description,
            "status": report.status,
            "lost_date": report.lost_date,
            "reward": report.reward,
            "contact_phone": report.contact_phone,
            "country": report.country,
            "department": report.department,
            "city": report.city,
            "address": report.address,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "published_at": report.published_at,
            "closed_at": report.closed_at,
        }

    @staticmethod
    def _to_list_item(report: LostReport) -> dict:
        return {
            "id": str(report.id),
            "pet_id": str(report.pet_id),
            "title": report.title,
            "status": report.status,
            "city": report.city,
            "lost_date": report.lost_date,
            "published_at": report.published_at,
        }