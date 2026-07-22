from datetime import date
from uuid import UUID
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import LostReportStatus
from app.models.report import LostReport
from app.models.pet import Pet


class LostReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, created_by: UUID, data: dict[str, Any]) -> LostReport:
        report = LostReport(created_by=created_by, **data)
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def get_by_id(self, report_id: UUID) -> LostReport | None:
        result = await self.db.execute(
            select(LostReport).where(LostReport.id == report_id, LostReport.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    def base_query(
        self,
        search: str | None = None,
        status: LostReportStatus | None = None,
        species_id: UUID | None = None,
        city: str | None = None,
        created_by: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort: str | None = None,
        order: str = "desc",
    ) -> Select:
        stmt = select(LostReport).where(LostReport.deleted_at.is_(None))

        if species_id:
            stmt = stmt.join(Pet, Pet.id == LostReport.pet_id).where(Pet.species_id == species_id)

        if search:
            stmt = stmt.where(LostReport.title.ilike(f"%{search}%"))
        if status:
            stmt = stmt.where(LostReport.status == status)
        if city:
            stmt = stmt.where(LostReport.city.ilike(city))
        if created_by:
            stmt = stmt.where(LostReport.created_by == created_by)
        if date_from:
            stmt = stmt.where(LostReport.lost_date >= date_from)
        if date_to:
            stmt = stmt.where(LostReport.lost_date <= date_to)

        sortable = {
            "lost_date": LostReport.lost_date,
            "published_at": LostReport.published_at,
            "created_at": LostReport.created_at,
        }
        column = sortable.get(sort, LostReport.published_at)
        stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
        return stmt

    async def update(self, report: LostReport, data: dict[str, Any]) -> LostReport:
        for field, value in data.items():
            setattr(report, field, value)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def soft_delete(self, report: LostReport) -> None:
        from datetime import datetime, timezone
        report.deleted_at = datetime.now(timezone.utc)
        report.is_active = False
        await self.db.flush()
