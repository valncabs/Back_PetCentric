from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ImageEntityType
from app.models.image import Image


class ImageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_entity(self, entity_type: ImageEntityType, entity_id: UUID) -> list[Image]:
        result = await self.db.execute(
            select(Image)
            .where(Image.entity_type == entity_type, Image.entity_id == entity_id)
            .order_by(Image.is_primary.desc(), Image.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, image_id: UUID) -> Image | None:
        return await self.db.get(Image, image_id)

    async def create(self, **data) -> Image:
        image = Image(**data)
        self.db.add(image)
        await self.db.flush()
        await self.db.refresh(image)
        return image

    async def unset_primary_for_entity(self, entity_type: ImageEntityType, entity_id: UUID) -> None:
        result = await self.db.execute(
            select(Image).where(
                Image.entity_type == entity_type,
                Image.entity_id == entity_id,
                Image.is_primary.is_(True),
            )
        )
        for image in result.scalars():
            image.is_primary = False
        await self.db.flush()

    async def delete(self, image: Image) -> None:
        await self.db.delete(image)
        await self.db.flush()