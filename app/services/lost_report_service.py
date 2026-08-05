from datetime import date, datetime, timezone
from uuid import UUID
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.enums import LostReportStatus, NotificationType
from app.models.report import LostReport
from app.models.pet import Pet
from app.repositories.found_report_repository import FoundReportRepository
from app.repositories.lost_report_repository import LostReportRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.pet_repository import PetRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.utils.pagination import PaginationParams, paginate
from app.utils.notify import admin_user_ids, notify_user


class LostReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.report_repo = LostReportRepository(db)
        self.pet_repo = PetRepository(db)
        self.found_report_repo = FoundReportRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.profile_repo = UserProfileRepository(db)

    async def create_report(self, user_id: UUID, data: dict[str, Any]) -> dict:
        pet = await self.pet_repo.get_by_id_for_owner(data["pet_id"], user_id)
        if pet is None:
            raise NotFoundException(
                "La mascota indicada no existe o no te pertenece.",
                errors={"pet_id": ["Mascota no encontrada."]},
            )

        active_report = await self.report_repo.get_active_by_pet(data["pet_id"])
        if active_report is not None:
            raise BadRequestException(
                "Esta mascota ya tiene un reporte de pérdida activo.",
                errors={
                    "pet_id": [
                        "Esta mascota ya está reportada como perdida. "
                        "Márcala como encontrada antes de reportarla de nuevo."
                    ]
                },
            )

        report = await self.report_repo.create(user_id, data)
        await self.db.commit()
        return await self._to_dict_with_pet(report)

    async def get_report(self, report_id: UUID) -> dict:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        return await self._to_dict_with_pet(report)

    async def list_reports(
    self,
    params: PaginationParams,
    status: LostReportStatus | None = None,
    species_id: UUID | None = None,
    city: str | None = None,
    created_by: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    ) -> dict:
        stmt = self.report_repo.base_query(
            params.search, status, species_id, city, created_by, date_from, date_to, params.sort, params.order
        )
        return await paginate(self.db, stmt, params, self._to_list_item)

    # agregar nuevo método, junto a close_report:
    async def admin_close_report(self, report_id: UUID) -> dict:
        """Cierre por parte de un admin, sin exigir ownership. Protegido en el
        router con require_permission('lost_reports.admin_manage')."""
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        if report.status == LostReportStatus.CLOSED:
            raise BadRequestException("El reporte ya está cerrado.")

        report.status = LostReportStatus.CLOSED
        report.closed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(report)
        return await self._to_dict_with_pet(report)

    async def admin_delete_report(self, report_id: UUID) -> None:
        """Eliminación por parte de un admin, sin exigir ownership."""
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        await self.report_repo.soft_delete(report)
        await self.db.commit()
        
    async def list_my_reports(self, user_id: UUID, params: PaginationParams) -> dict:
        return await self.list_reports(params, created_by=user_id)

    async def update_report(self, report_id: UUID, user_id: UUID, data: dict[str, Any]) -> dict:
        report = await self._get_owned_editable_report(report_id, user_id)
        update_data = {field: value for field, value in data.items() if value is not None}
        report = await self.report_repo.update(report, update_data)
        await self.db.commit()
        return await self._to_dict_with_pet(report)

    async def delete_report(self, report_id: UUID, user_id: UUID) -> None:
        report = await self._get_owned_report(report_id, user_id)
        await self.report_repo.soft_delete(report)
        await self.db.commit()

    async def request_mark_as_found(self, report_id: UUID, user_id: UUID) -> dict:
        """El dueño solicita marcar su mascota como encontrada. NO cambia el
        estado directamente: el admin es quien aprueba el cambio a FOUND.
        Se notifica a todos los admins para que revisen la solicitud."""
        report = await self._get_owned_report(report_id, user_id)
        if report.status != LostReportStatus.PUBLISHED:
            raise BadRequestException(
                "Solo un reporte publicado puede solicitar marcarse como encontrado."
            )

        report.found_requested_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(report)

        for admin_id in await admin_user_ids(self.db):
            await notify_user(
                self.db,
                admin_id,
                "Solicitud de mascota encontrada",
                f"El dueño del reporte '{report.title}' solicita marcar su mascota como "
                "encontrada. Revisa y aprueba el cambio.",
                type_=NotificationType.SYSTEM,
            )

        return await self._to_dict_with_pet(report)

    async def admin_mark_found(self, report_id: UUID) -> dict:
        """El admin aprueba la solicitud del dueño y cambia 100% el estado a
        FOUND. Solo se permite si el dueño solicitó antes (found_requested_at).
        Notifica al dueño y, si había un avistamiento aprobado o confirmado
        vinculado, también a quien lo reportó."""
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise NotFoundException("Reporte no encontrado.")
        if report.status == LostReportStatus.FOUND:
            raise BadRequestException("El reporte ya está marcado como encontrado.")
        if report.found_requested_at is None:
            raise BadRequestException(
                "El dueño debe solicitar primero marcar su mascota como encontrada."
            )

        report.status = LostReportStatus.FOUND
        report.closed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(report)

        await notify_user(
            self.db,
            report.created_by,
            "¡Tu mascota fue confirmada como encontrada!",
            f"El reporte '{report.title}' fue marcado como encontrado. ¡Felicidades!",
            type_=NotificationType.FOUND_MATCH,
        )

        witnesses = await self._witnesses_to_notify(report.id)
        for witness_id, title in witnesses:
            await notify_user(
                self.db,
                witness_id,
                "¡La mascota fue encontrada!",
                f"La mascota del reporte '{title}' fue confirmada como encontrada. "
                "¡Gracias por tu ayuda!",
                type_=NotificationType.FOUND_MATCH,
            )

        return await self._to_dict_with_pet(report)

    async def close_report(self, report_id: UUID, user_id: UUID) -> dict:
        report = await self._get_owned_report(report_id, user_id)
        if report.status == LostReportStatus.CLOSED:
            raise BadRequestException("El reporte ya está cerrado.")

        report.status = LostReportStatus.CLOSED
        report.closed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(report)
        return await self._to_dict_with_pet(report)

    async def _witnesses_to_notify(self, lost_report_id: UUID) -> list[tuple[UUID, str]]:
        """Avistamientos MATCHED/APPROVED/REJECTED de un reporte: sus autores
        participaron en el flujo y deben enterarse del desenlace."""
        from app.models.enums import FoundReportStatus
        from app.models.report import FoundReport

        result = await self.db.execute(
            select(FoundReport)
            .where(
                FoundReport.lost_report_id == lost_report_id,
                FoundReport.deleted_at.is_(None),
                FoundReport.status.in_(
                    [
                        FoundReportStatus.MATCHED,
                        FoundReportStatus.APPROVED,
                        FoundReportStatus.REJECTED,
                    ]
                ),
            )
        )
        seen: dict[UUID, str] = {}
        for report in result.scalars():
            if report.created_by not in seen:
                seen[report.created_by] = report.title
        return list(seen.items())

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

    async def _to_dict_with_pet(self, report: LostReport) -> dict:
        pet = await self.pet_repo.get_by_id_ignoring_owner(report.pet_id)
        return self._to_dict(report, pet)

    @staticmethod
    def _to_dict(report: LostReport, pet: Pet | None) -> dict:
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
            "found_requested_at": report.found_requested_at,
            "pet_name": pet.name if pet else "",
            "pet_species_id": str(pet.species_id) if pet else "",
            "pet_breed_id": str(pet.breed_id) if pet and pet.breed_id else None,
            "pet_sex": pet.sex if pet else "",
            "pet_color": pet.color if pet else "",
            "pet_size": pet.size if pet else "",
            "pet_approximate_age": pet.approximate_age if pet else None,
            "pet_distinctive_marks": pet.distinctive_marks if pet else None,
        }

    @staticmethod
    def _to_list_item(report: LostReport) -> dict:
        return {
            "id": str(report.id),
            "pet_id": str(report.pet_id),
            "created_by": str(report.created_by),
            "title": report.title,
            "status": report.status,
            "city": report.city,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "lost_date": report.lost_date,
            "published_at": report.published_at,
            "found_requested_at": report.found_requested_at,
        }