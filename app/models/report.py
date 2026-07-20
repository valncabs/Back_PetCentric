from __future__ import annotations
import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import FoundReportStatus, LostReportStatus

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.pet import Pet, Species
    from app.models.user import User

class LostReport(Base):
    __tablename__ = "lost_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pets.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[LostReportStatus] = mapped_column(
        SAEnum(LostReportStatus, name="lost_report_status_enum", create_type=False),
        default=LostReportStatus.PUBLISHED,
        nullable=False,
    )
    lost_date: Mapped[date] = mapped_column(Date, nullable=False)
    reward: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pet: Mapped["Pet"] = relationship("Pet", back_populates="lost_reports")
    reporter: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by], back_populates="lost_reports"
    )


class FoundReport(Base):
    __tablename__ = "found_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[FoundReportStatus] = mapped_column(
        SAEnum(FoundReportStatus, name="found_report_status_enum", create_type=False),
        default=FoundReportStatus.PUBLISHED,
        nullable=False,
    )
    found_date: Mapped[date] = mapped_column(Date, nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    species_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("species.id"), nullable=True)
    lost_report_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("lost_reports.id"), nullable=True)

    species: Mapped["Species | None"] = relationship("Species")
    lost_report: Mapped["LostReport | None"] = relationship("LostReport")
    reporter: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by], back_populates="found_reports"
    )
    approver: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by])
