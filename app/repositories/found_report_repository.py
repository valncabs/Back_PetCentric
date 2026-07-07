from uuid import UUID
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FoundReportStatus
from app.models.report import FoundReport


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

    def base_query(
        self, search: str | None = None, status: FoundReportStatus | None = None,
        sort: str | None = None, order: str = "desc",
    ) -> Select:
        stmt = select(FoundReport).where(FoundReport.deleted_at.is_(None))
        if search:
            stmt = stmt.where(FoundReport.title.ilike(f"%{search}%"))
        if status:
            stmt = stmt.where(FoundReport.status == status)

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