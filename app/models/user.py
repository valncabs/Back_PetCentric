from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Enum as SAEnum
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
    lost_reports: Mapped[list["LostReport"]] = relationship("LostReport", back_populates="created_by")
    found_reports: Mapped[list["FoundReport"]] = relationship("FoundReport", foreign_keys="FoundReport.created_by_id", back_populates="created_by")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="sender")
    images: Mapped[list["Image"]] = relationship("Image", back_populates="uploaded_by")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_type: Mapped[DocumentType | None] = mapped_column(SAEnum(DocumentType), nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    gender: Mapped[Gender | None] = mapped_column(SAEnum(Gender), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)

    # Relaciones
    user: Mapped["User"] = relationship("User", back_populates="profile")