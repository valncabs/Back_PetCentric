from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import LostReportStatus, FoundReportStatus, ImageEntityType


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.pet import Pet
class LostReport(Base):
    __tablename__ = "lost_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[LostReportStatus] = mapped_column(
        SAEnum(LostReportStatus), default=LostReportStatus.PUBLISHED, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    lost_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    pet: Mapped["Pet"] = relationship("Pet", back_populates="lost_reports")
    created_by: Mapped["User"] = relationship("User", back_populates="lost_reports")
    images: Mapped[list["Image"]] = relationship(
        "Image",
        primaryjoin="and_(Image.entity_id == LostReport.id, Image.entity_type == 'LOST_REPORT')",
        foreign_keys="Image.entity_id",
        viewonly=True,
    )


class FoundReport(Base):
    __tablename__ = "found_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[FoundReportStatus] = mapped_column(
        SAEnum(FoundReportStatus), default=FoundReportStatus.PUBLISHED, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    found_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    found_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id], back_populates="found_reports")
    approved_by: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by_id])
    images: Mapped[list["Image"]] = relationship(
        "Image",
        primaryjoin="and_(Image.entity_id == FoundReport.id, Image.entity_type == 'FOUND_REPORT')",
        foreign_keys="Image.entity_id",
        viewonly=True,
    )


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[ImageEntityType] = mapped_column(SAEnum(ImageEntityType), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    public_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    uploaded_by: Mapped["User"] = relationship("User", back_populates="images")