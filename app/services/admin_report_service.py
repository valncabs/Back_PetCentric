from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FoundReportStatus, LostReportStatus
from app.repositories.found_report_repository import FoundReportRepository
from app.repositories.lost_report_repository import LostReportRepository


class AdminReportService:
    """Combina lost_reports y found_reports en una sola vista paginada para
    el panel de admin. No reutiliza `paginate()` porque ese helper opera
    sobre un único Select; acá se pagina en memoria tras unir y ordenar."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.lost_repo = LostReportRepository(db)
        self.found_repo = FoundReportRepository(db)

    async def list_all_reports(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        report_type: str | None = None,
        species_id: UUID | None = None,
        status: str | None = None,
        city: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        items: list[dict] = []

        # El status puede pertenecer solo a uno de los dos enums (p. ej. 'FOUND'
        # es válido en LostReportStatus pero no existe en FoundReportStatus).
        # Si no pertenece al enum de esa rama, esa rama simplemente no se
        # consulta, en vez de lanzar ValueError.
        lost_status = None
        if status:
            try:
                lost_status = LostReportStatus(status)
            except ValueError:
                lost_status = None

        found_status = None
        if status:
            try:
                found_status = FoundReportStatus(status)
            except ValueError:
                found_status = None

        # Si el status filtrado no existe en NINGUNO de los dos enums, es un
        # valor inválido de verdad: no devolvemos nada en vez de ignorar el
        # filtro silenciosamente.
        status_is_invalid = bool(status) and lost_status is None and found_status is None

        if not status_is_invalid:
            if report_type != "FOUND" and (not status or lost_status is not None):
                lost_stmt = self.lost_repo.base_query(
                    search=search, status=lost_status, species_id=species_id,
                    city=city, date_from=date_from, date_to=date_to,
                )
                lost_rows = (await self.db.execute(lost_stmt)).scalars().all()
                items += [self._lost_to_item(r) for r in lost_rows]

            if report_type != "LOST" and (not status or found_status is not None):
                found_stmt = self.found_repo.base_query(
                    search=search, status=found_status, species_id=species_id,
                    city=city, date_from=date_from, date_to=date_to,
                )
                found_rows = (await self.db.execute(found_stmt)).scalars().all()
                items += [self._found_to_item(r) for r in found_rows]

        items.sort(key=lambda i: i["published_at"], reverse=True)

        total = len(items)
        start = (page - 1) * page_size
        page_items = items[start : start + page_size]
        pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "items": page_items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": pages,
        }

    @staticmethod
    def _lost_to_item(report) -> dict:
        return {
            "id": str(report.id),
            "type": "LOST",
            "created_by": str(report.created_by),
            "title": report.title,
            "status": report.status,
            "city": report.city,
            "date": report.lost_date,
            "published_at": report.published_at,
        }

    @staticmethod
    def _found_to_item(report) -> dict:
        return {
            "id": str(report.id),
            "type": "FOUND",
            "created_by": str(report.created_by),
            "title": report.title,
            "status": report.status,
            "city": report.city,
            "date": report.found_date,
            "published_at": report.published_at,
        }