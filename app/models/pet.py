from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Boolean
from sqlalchemy import DateTime, Float, ForeignKey, String, Boolean, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import PetSex, PetSize


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.report import LostReport, Image

class Species(Base):
    __tablename__ = "species"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # ← agregar
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    breeds: Mapped[list["Breed"]] = relationship("Breed", back_populates="species")
    pets: Mapped[list["Pet"]] = relationship("Pet", back_populates="species")



class Breed(Base):
    __tablename__ = "breeds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    species_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("species.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # ← agregar
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    species: Mapped["Species"] = relationship("Species", back_populates="breeds")
    pets: Mapped[list["Pet"]] = relationship("Pet", back_populates="breed")

class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    species_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("species.id"), nullable=False)
    breed_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("breeds.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sex: Mapped[PetSex] = mapped_column(
        SAEnum(PetSex, name="pet_sex_enum", create_type=False), nullable=False
    )
    color: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[PetSize] = mapped_column(
        SAEnum(PetSize, name="size_enum", create_type=False), nullable=False
    )
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    approximate_age: Mapped[int | None] = mapped_column(nullable=True)   # ← int, no String
    microchip_number: Mapped[str | None] = mapped_column(String(100), nullable=True)   # ← sin unique=True
    sterilized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    distinctive_marks: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)   # ← faltaba
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped["User"] = relationship("User", back_populates="pets")
    species: Mapped["Species"] = relationship("Species", back_populates="pets")
    breed: Mapped["Breed | None"] = relationship("Breed", back_populates="pets")
    
    lost_reports: Mapped[list["LostReport"]] = relationship("LostReport", back_populates="pet")
    images: Mapped[list["Image"]] = relationship(
        "Image",
        primaryjoin="and_(Image.entity_id == Pet.id, Image.entity_type == 'PET')",
        foreign_keys="Image.entity_id",
        viewonly=True,
    )