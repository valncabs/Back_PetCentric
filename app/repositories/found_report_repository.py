from uuid import UUID
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FoundReportStatus
from app.models.report import FoundReport
from datetime import date

class FoundReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, created_by: UUID, data: dict[str, Any]) -> FoundReport:
        report = FoundReport(created_by=created_by, **data)
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def get_by_id(self, report_id: UUID) -> FoundReport | None:
        result = await self.db.execute(
            select(FoundReport).where(FoundReport.id == report_id, FoundReport.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_by_lost_report(self, lost_report_id: UUID) -> list[FoundReport]:
        """Todos los avistamientos asociados a un reporte de pérdida, del más
        reciente al más antiguo. Usado en 'Mis reportes' para que el dueño
        revise cada candidato."""
        result = await self.db.execute(
            select(FoundReport)
            .where(
                FoundReport.lost_report_id == lost_report_id,
                FoundReport.deleted_at.is_(None),
            )
            .order_by(FoundReport.published_at.desc())
        )
        return list(result.scalars().all())

    def base_query(
    self,
    search: str | None = None,
    status: FoundReportStatus | None = None,
    species_id: UUID | None = None,
    city: str | None = None,
    created_by: UUID | None = None,
    lost_report_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: str | None = None,
    order: str = "desc",
    ) -> Select:
        stmt = select(FoundReport).where(FoundReport.deleted_at.is_(None))

        if search:
            stmt = stmt.where(FoundReport.title.ilike(f"%{search}%"))
        if status:
            stmt = stmt.where(FoundReport.status == status)
        if species_id:
            stmt = stmt.where(FoundReport.species_id == species_id)
        if city:
            stmt = stmt.where(FoundReport.city.ilike(city))
        if created_by:
            stmt = stmt.where(FoundReport.created_by == created_by)
        if lost_report_id:
            stmt = stmt.where(FoundReport.lost_report_id == lost_report_id)
        if date_from:
            stmt = stmt.where(FoundReport.found_date >= date_from)
        if date_to:
            stmt = stmt.where(FoundReport.found_date <= date_to)

        sortable = {
            "found_date": FoundReport.found_date,
            "published_at": FoundReport.published_at,
            "created_at": FoundReport.created_at,
        }
        column = sortable.get(sort, FoundReport.published_at)
        stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
        return stmt

    async def update(self, report: FoundReport, data: dict[str, Any]) -> FoundReport:
        for field, value in data.items():
            setattr(report, field, value)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def bulk_reject_others(self, lost_report_id: UUID, keep_report_id: UUID) -> None:
        """Al aprobar un avistamiento como definitivo, todos los demás
        avistamientos activos del mismo reporte de pérdida se rechazan:
        la mascota ya apareció, no tiene sentido seguir revisando candidatos."""
        result = await self.db.execute(
            select(FoundReport).where(
                FoundReport.lost_report_id == lost_report_id,
                FoundReport.id != keep_report_id,
                FoundReport.status.in_([FoundReportStatus.PUBLISHED, FoundReportStatus.MATCHED]),
                FoundReport.deleted_at.is_(None),
            )
        )
        for report in result.scalars():
            report.status = FoundReportStatus.REJECTED
        await self.db.flush()

    async def soft_delete(self, report: FoundReport) -> None:
        from datetime import datetime, timezone
        report.deleted_at = datetime.now(timezone.utc)
        report.is_active = False
        await self.db.flush()