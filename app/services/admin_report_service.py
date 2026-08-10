from datetime import date
from uuid import UUID

from sqlalchemy import String, cast, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FoundReportStatus, LostReportStatus
from app.models.pet import Pet
from app.models.report import FoundReport, LostReport


class AdminReportService:
    """Combina lost_reports y found_reports en una sola vista paginada para
    el panel de admin. La combinación, el filtrado y el orden se resuelven en
    la BD (UNION ALL + COUNT + OFFSET/LIMIT), no en memoria."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

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
        # valor inválido de verdad: _combined_query no genera ninguna rama y
        # la consulta devuelve vacío en vez de ignorar el filtro en silencio.

        stmt = self._combined_query(
            search=search,
            report_type=report_type,
            status=status,
            lost_status=lost_status,
            found_status=found_status,
            species_id=species_id,
            city=city,
            date_from=date_from,
            date_to=date_to,
        )

        if stmt is None:
            total = 0
            items = []
        else:
            total = int(
                (
                    await self.db.execute(
                        select(func.count()).select_from(stmt.subquery())
                    )
                ).scalar_one()
                or 0
            )
            rows = (
                await self.db.execute(
                    stmt.offset((page - 1) * page_size).limit(page_size)
                )
            ).all()
            items = [self._row_to_item(row) for row in rows]

        pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": pages,
        }

    def _combined_query(
        self,
        search: str | None,
        report_type: str | None,
        status: str | None,
        lost_status: LostReportStatus | None,
        found_status: FoundReportStatus | None,
        species_id: UUID | None,
        city: str | None,
        date_from: date | None,
        date_to: date | None,
    ):
        branches = []

        # Con status: solo participa la rama cuyo enum reconoce ese valor.
        # Sin status: ambas ramas participan (salvo que report_type las excluya).
        include_lost = report_type != "FOUND" and (not status or lost_status is not None)
        include_found = report_type != "LOST" and (not status or found_status is not None)

        if include_lost:
            branches.append(
                self._lost_projection(
                    search=search,
                    status=lost_status,
                    species_id=species_id,
                    city=city,
                    date_from=date_from,
                    date_to=date_to,
                )
            )

        if include_found:
            branches.append(
                self._found_projection(
                    search=search,
                    status=found_status,
                    species_id=species_id,
                    city=city,
                    date_from=date_from,
                    date_to=date_to,
                )
            )

        if not branches:
            return None

        combined = union_all(*branches) if len(branches) > 1 else branches[0]
        sub = combined.subquery()
        return select(sub).order_by(sub.c.published_at.desc(), sub.c.id.desc())

    def _lost_projection(
        self,
        search: str | None,
        status: LostReportStatus | None,
        species_id: UUID | None,
        city: str | None,
        date_from: date | None,
        date_to: date | None,
    ):
        stmt = (
            select(
                LostReport.id.label("id"),
                literal("LOST", String).label("type"),
                cast(LostReport.created_by, String).label("created_by"),
                LostReport.title.label("title"),
                cast(LostReport.status, String).label("status"),
                LostReport.city.label("city"),
                LostReport.lost_date.label("date"),
                LostReport.published_at.label("published_at"),
                LostReport.found_requested_at.label("found_requested_at"),
            )
            .where(LostReport.deleted_at.is_(None))
        )

        if species_id:
            stmt = stmt.join(Pet, Pet.id == LostReport.pet_id).where(
                Pet.species_id == species_id
            )
        if search:
            stmt = stmt.where(LostReport.title.ilike(f"%{search}%"))
        if status:
            stmt = stmt.where(LostReport.status == status)
        if city:
            stmt = stmt.where(LostReport.city.ilike(city))
        if date_from:
            stmt = stmt.where(LostReport.lost_date >= date_from)
        if date_to:
            stmt = stmt.where(LostReport.lost_date <= date_to)
        return stmt

    def _found_projection(
        self,
        search: str | None,
        status: FoundReportStatus | None,
        species_id: UUID | None,
        city: str | None,
        date_from: date | None,
        date_to: date | None,
    ):
        from sqlalchemy import DateTime

        stmt = (
            select(
                FoundReport.id.label("id"),
                literal("FOUND", String).label("type"),
                cast(FoundReport.created_by, String).label("created_by"),
                FoundReport.title.label("title"),
                cast(FoundReport.status, String).label("status"),
                FoundReport.city.label("city"),
                FoundReport.found_date.label("date"),
                FoundReport.published_at.label("published_at"),
                literal(None, DateTime(timezone=True)).label("found_requested_at"),
            )
            .where(FoundReport.deleted_at.is_(None))
        )

        if species_id:
            stmt = stmt.where(FoundReport.species_id == species_id)
        if search:
            stmt = stmt.where(FoundReport.title.ilike(f"%{search}%"))
        if status:
            stmt = stmt.where(FoundReport.status == status)
        if city:
            stmt = stmt.where(FoundReport.city.ilike(city))
        if date_from:
            stmt = stmt.where(FoundReport.found_date >= date_from)
        if date_to:
            stmt = stmt.where(FoundReport.found_date <= date_to)
        return stmt

    @staticmethod
    def _row_to_item(row) -> dict:
        return {
            "id": row.id,
            "type": row.type,
            "created_by": row.created_by,
            "title": row.title,
            "status": row.status,
            "city": row.city,
            "date": row.date,
            "published_at": row.published_at,
            "found_requested_at": row.found_requested_at,
        }
