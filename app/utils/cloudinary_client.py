import cloudinary
import cloudinary.uploader

from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


def upload_image(file_bytes: bytes, folder: str) -> dict:
    """Sube una imagen a Cloudinary. Es SÍNCRONA (bloqueante) a propósito:
    el SDK de Cloudinary no ofrece cliente async — por eso se llama siempre
    envuelta en un threadpool desde el service (ver ImageService)."""
    result = cloudinary.uploader.upload(file_bytes, folder=folder, resource_type="image")
    return {
        "public_id": result["public_id"],
        "secure_url": result["secure_url"],
    }


def delete_image(public_id: str) -> None:
    cloudinary.uploader.destroy(public_id, resource_type="image")