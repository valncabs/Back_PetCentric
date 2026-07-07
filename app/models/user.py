from __future__ import annotations
import uuid
from datetime import datetime, date

from decimal import Decimal
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import DocumentType, Gender

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.pet import Pet
    from app.models.auth import UserRole, UserPermission
    from app.models.report import LostReport, FoundReport, Image
    from app.models.communication import Notification, Message
    from app.models.audit import AuditLog

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="user", uselist=False)
    pets: Mapped[list["Pet"]] = relationship("Pet", back_populates="owner")
    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="user")
    user_permissions: Mapped[list["UserPermission"]] = relationship("UserPermission", back_populates="user")
    lost_reports: Mapped[list["LostReport"]] = relationship("LostReport", foreign_keys="LostReport.created_by", back_populates="reporter")
    found_reports: Mapped[list["FoundReport"]] = relationship("FoundReport", foreign_keys="FoundReport.created_by", back_populates="reporter")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="sender")
    images: Mapped[list["Image"]] = relationship("Image", back_populates="uploader")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type_enum", create_type=False), nullable=False
    )
    document_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[Gender | None] = mapped_column(
        SAEnum(Gender, name="gender_enum", create_type=False)
    )
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="profile")