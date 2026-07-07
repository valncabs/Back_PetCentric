from uuid import UUID
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import LostReportStatus
from app.models.report import LostReport


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
        self, search: str | None = None, status: LostReportStatus | None = None,
        sort: str | None = None, order: str = "desc",
    ) -> Select:
        stmt = select(LostReport).where(LostReport.deleted_at.is_(None))

        if search:
            stmt = stmt.where(LostReport.title.ilike(f"%{search}%"))
        if status:
            stmt = stmt.where(LostReport.status == status)

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