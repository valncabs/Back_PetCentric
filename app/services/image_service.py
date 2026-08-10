from uuid import UUID
import logging

from anyio import to_thread
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.enums import ImageEntityType
from app.models.image import Image
from app.repositories.image_repository import ImageRepository
from app.utils.cloudinary_client import delete_image as cloudinary_delete, upload_image as cloudinary_upload

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
CHUNK_SIZE = 64 * 1024  # 64 KB

_MAGIC_JPG = b"\xff\xd8\xff"
_MAGIC_PNG = b"\x89PNG\r\n\x1a\n"
_MAGIC_WEBP_RIFF = b"RIFF"
_MAGIC_WEBP_ID = b"WEBP"

_log = logging.getLogger(__name__)


def _detect_image_mime(content: bytes) -> str | None:
    """Detecta el tipo real de imagen por sus magic bytes. Ignora por completo
    el content-type que manda el cliente, que es fácil de falsificar."""
    if content.startswith(_MAGIC_JPG):
        return "image/jpeg"
    if content.startswith(_MAGIC_PNG):
        return "image/png"
    if (
        len(content) >= 12
        and content.startswith(_MAGIC_WEBP_RIFF)
        and content[8:12] == _MAGIC_WEBP_ID
    ):
        return "image/webp"
    return None


class ImageService:
    """Genérico: no conoce reglas de dueño. El router/servicio del recurso
    padre (pets, lost-reports, found-reports) valida ownership ANTES de llamar aquí."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.image_repo = ImageRepository(db)

    async def upload(
        self,
        entity_type: ImageEntityType,
        entity_id: UUID,
        uploaded_by: UUID,
        file: UploadFile,
        set_as_primary: bool = False,
    ) -> dict:
        content = await self._read_limited(file)
        mime_type = self._validate_file(content)

        folder = f"pet-centric/{entity_type.value.lower()}/{entity_id}"
        result = await to_thread.run_sync(cloudinary_upload, content, folder)

        if set_as_primary:
            await self.image_repo.unset_primary_for_entity(entity_type, entity_id)

        image = await self.image_repo.create(
            entity_type=entity_type,
            entity_id=entity_id,
            file_name=result["public_id"],
            file_path=result["secure_url"],
            mime_type=mime_type,
            file_size=len(content),
            is_primary=set_as_primary,
            uploaded_by=uploaded_by,
        )
        await self.db.commit()
        _log.info(
            "Imagen subida: entity=%s entity_id=%s image_id=%s mime=%s bytes=%d",
            entity_type.value,
            entity_id,
            image.id,
            mime_type,
            len(content),
        )
        return self._to_dict(image)

    async def list_for_entity(self, entity_type: ImageEntityType, entity_id: UUID) -> list[dict]:
        images = await self.image_repo.list_by_entity(entity_type, entity_id)
        return [self._to_dict(image) for image in images]

    async def delete(self, image_id: UUID, entity_type: ImageEntityType, entity_id: UUID) -> None:
        image = await self.image_repo.get_by_id(image_id)
        if image is None or image.entity_type != entity_type or image.entity_id != entity_id:
            raise NotFoundException("Imagen no encontrada.")

        await to_thread.run_sync(cloudinary_delete, image.file_name)
        await self.image_repo.delete(image)
        await self.db.commit()
        _log.info("Imagen eliminada: image_id=%s entity=%s entity_id=%s", image_id, entity_type.value, entity_id)

    async def _read_limited(self, file: UploadFile) -> bytes:
        """Lee el archivo por chunks y aborta en cuanto se supera el límite de
        tamaño, sin llegar a bufferizar el archivo completo en memoria."""
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_FILE_SIZE_BYTES:
                raise BadRequestException(
                    "El archivo es demasiado grande.",
                    errors={"file": ["El tamaño máximo permitido es 5MB."]},
                )
            chunks.append(chunk)
        return b"".join(chunks)

    def _validate_file(self, content: bytes) -> str:
        """Valida el contenido real por magic bytes y devuelve el MIME detectado."""
        if not content:
            raise BadRequestException(
                "El archivo está vacío.",
                errors={"file": ["El archivo no puede estar vacío."]},
            )
        mime_type = _detect_image_mime(content)
        if mime_type is None or mime_type not in ALLOWED_MIME_TYPES:
            raise BadRequestException(
                "Formato de imagen no soportado.",
                errors={"file": ["Solo se permiten imágenes JPEG, PNG o WEBP reales."]},
            )
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise BadRequestException(
                "El archivo es demasiado grande.",
                errors={"file": ["El tamaño máximo permitido es 5MB."]},
            )
        return mime_type

    @staticmethod
    def _to_dict(image: Image) -> dict:
        return {
            "id": str(image.id),
            "entity_type": image.entity_type,
            "entity_id": str(image.entity_id),
            "url": image.file_path,
            "mime_type": image.mime_type,
            "file_size": image.file_size,
            "is_primary": image.is_primary,
        }