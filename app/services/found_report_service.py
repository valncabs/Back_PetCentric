from datetime import date, datetime, timezone
from uuid import UUID
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.enums import FoundReportStatus, LostReportStatus, NotificationType
from app.models.report import FoundReport
from app.repositories.found_report_repository import FoundReportRepository
from app.repositories.lost_report_repository import LostReportRepository
from app.repositories.notification_repository import NotificationRepository
from app.utils.pagination import PaginationParams, paginate


class FoundReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.report_repo = FoundReportRepository(db)
        self.lost_report_repo = LostReportRepository(db)
        self.notification_repo = NotificationRepository(db)

    async def create_report(self, user_id: UUID, data: dict[str, Any]) -> dict:
        lost_report_id = data.get("lost_report_id")
        if lost_report_id:
            lost_report = await self.lost_report_repo.get_by_id(lost_report_id)
            if lost_report is None:
                raise NotFoundException("El reporte de mascota perdida no existe.")
            if lost_report.status != LostReportStatus.PUBLISHED:
                raise BadRequestException(
                    "Esta mascota ya fue encontrada. No se pueden reportar más avistamientos.",
                    errors={"lost_report_id": ["El reporte ya no está activo."]},
                )

        report = await self.report_repo.create(user_id, data)
        await self.db.commit()
        return self._to_dict(report)

    async def get_report(self, report_id: UUID) -> dict:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        return self._to_dict(report)

    async def list_reports(
    self,
    params: PaginationParams,
    status: FoundReportStatus | None = None,
    species_id: UUID | None = None,
    city: str | None = None,
    created_by: UUID | None = None,
    lost_report_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    ) -> dict:
        stmt = self.report_repo.base_query(
            params.search, status, species_id, city, created_by, lost_report_id,
            date_from, date_to, params.sort, params.order
        )
        return await paginate(self.db, stmt, params, self._to_list_item)

    # agregar nuevo método, junto a close_report:
    async def admin_close_report(self, report_id: UUID) -> dict:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        if report.status == FoundReportStatus.CLOSED:
            raise BadRequestException("El reporte ya está cerrado.")

        report.status = FoundReportStatus.CLOSED
        report.closed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(report)
        return self._to_dict(report)

    async def admin_delete_report(self, report_id: UUID) -> None:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        await self.report_repo.soft_delete(report)
        await self.db.commit()
        
    async def list_my_reports(self, user_id: UUID, params: PaginationParams) -> dict:
        return await self.list_reports(params, created_by=user_id)

    async def list_by_lost_report(self, lost_report_id: UUID) -> list[dict]:
        """Todos los avistamientos asociados a un reporte de pérdida, para que
        el dueño los revise en 'Mis reportes'."""
        reports = await self.report_repo.list_by_lost_report(lost_report_id)
        return [self._to_dict(r) for r in reports]

    async def update_report(self, report_id: UUID, user_id: UUID, data: dict[str, Any]) -> dict:
        report = await self.verify_ownership(report_id, user_id)
        if report.status != FoundReportStatus.PUBLISHED:
            raise BadRequestException("Solo se puede editar un reporte mientras está publicado.")

        update_data = {field: value for field, value in data.items() if value is not None}
        report = await self.report_repo.update(report, update_data)
        await self.db.commit()
        return self._to_dict(report)

    async def delete_report(self, report_id: UUID, user_id: UUID) -> None:
        report = await self.verify_ownership(report_id, user_id)
        await self.report_repo.soft_delete(report)
        await self.db.commit()

    # ---------- Flujo de coincidencia (dueño del lost_report) ----------

    async def match_report(self, report_id: UUID, lost_report_owner_id: UUID) -> dict:
        """El dueño del reporte de pérdida marca este avistamiento como
        candidato. No bloquea otros avistamientos: puede haber varios
        MATCHED a la vez mientras el dueño investiga."""
        report, _ = await self._get_report_for_lost_report_owner(report_id, lost_report_owner_id)

        if report.status != FoundReportStatus.PUBLISHED:
            raise BadRequestException("Solo se puede marcar como coincidencia un avistamiento pendiente de revisión.")

        report.status = FoundReportStatus.MATCHED
        await self.db.commit()
        await self.db.refresh(report)
        return self._to_dict(report)

    async def unmatch_report(self, report_id: UUID, lost_report_owner_id: UUID) -> dict:
        """El dueño descarta un candidato que había marcado como MATCHED,
        sin necesidad de esperar al admin (por ejemplo, si ya no puede
        contactar a la persona o decide que no era su mascota)."""
        report, _ = await self._get_report_for_lost_report_owner(report_id, lost_report_owner_id)

        if report.status != FoundReportStatus.MATCHED:
            raise BadRequestException("Solo se puede descartar un avistamiento en estado de coincidencia.")

        report.status = FoundReportStatus.PUBLISHED
        report.owner_confirmed_at = None
        await self.db.commit()
        await self.db.refresh(report)
        return self._to_dict(report)

    async def confirm_found(self, report_id: UUID, lost_report_owner_id: UUID) -> dict:
        """El dueño confirma, tras reunirse en persona, que esta es su
        mascota. Queda pendiente de aprobación final del admin: el estado
        del avistamiento sigue en MATCHED, solo se marca la confirmación."""
        report, _ = await self._get_report_for_lost_report_owner(report_id, lost_report_owner_id)

        if report.status != FoundReportStatus.MATCHED:
            raise BadRequestException(
                "Debes marcar este avistamiento como coincidencia antes de confirmar el encuentro."
            )

        report.owner_confirmed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(report)
        return self._to_dict(report)

    async def _get_report_for_lost_report_owner(
        self, report_id: UUID, user_id: UUID
    ) -> tuple[FoundReport, Any]:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Avistamiento no encontrado.")
        if report.lost_report_id is None:
            raise BadRequestException("Este avistamiento no está asociado a un reporte de mascota perdida.")

        lost_report = await self.lost_report_repo.get_by_id(report.lost_report_id)
        if lost_report is None:
            raise NotFoundException("El reporte de mascota perdida asociado no existe.")
        if lost_report.created_by != user_id:
            raise ForbiddenException("No tienes permiso sobre el reporte de mascota perdida asociado.")

        return report, lost_report

    # ---------- Aprobación / rechazo (admin) ----------

    async def approve_report(self, report_id: UUID, admin_user_id: UUID) -> dict:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        if report.status != FoundReportStatus.MATCHED:
            raise BadRequestException("Solo se puede aprobar un avistamiento marcado como coincidencia.")
        if report.owner_confirmed_at is None:
            raise BadRequestException(
                "El dueño de la mascota debe confirmar el encuentro antes de que puedas aprobarlo."
            )

        report.status = FoundReportStatus.APPROVED
        report.approved_by = admin_user_id
        report.approved_at = datetime.now(timezone.utc)

        if report.lost_report_id:
            lost_report = await self.lost_report_repo.get_by_id(report.lost_report_id)
            if lost_report:
                lost_report.status = LostReportStatus.FOUND
                lost_report.closed_at = datetime.now(timezone.utc)

                await self.report_repo.bulk_reject_others(lost_report.id, report.id)

                await self.notification_repo.create(
                    user_id=lost_report.created_by,
                    title="¡Tu mascota fue confirmada como encontrada!",
                    message=f"El avistamiento reportado para '{lost_report.title}' fue aprobado. ¡Felicidades!",
                    type_=NotificationType.FOUND_MATCH,
                )

        await self.db.commit()
        await self.db.refresh(report)
        return self._to_dict(report)

    async def reject_report(self, report_id: UUID, admin_user_id: UUID) -> dict:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        if report.status not in (FoundReportStatus.PUBLISHED, FoundReportStatus.MATCHED):
            raise BadRequestException("Solo se puede rechazar un avistamiento pendiente o en coincidencia.")

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
            "lost_report_id": str(report.lost_report_id) if report.lost_report_id else None,
            "species_id": str(report.species_id) if report.species_id else None,
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
            "owner_confirmed_at": report.owner_confirmed_at,
            "published_at": report.published_at,
            "closed_at": report.closed_at,
        }

    @staticmethod
    def _to_list_item(report: FoundReport) -> dict:
        return {
            "id": str(report.id),
            "created_by": str(report.created_by),
            "species_id": str(report.species_id) if report.species_id else None,
            "title": report.title,
            "status": report.status,
            "city": report.city,
            "found_date": report.found_date,
            "published_at": report.published_at,
        }