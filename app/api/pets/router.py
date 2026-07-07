from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import File, UploadFile
from app.models.enums import ImageEntityType
from app.services.image_service import ImageService
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.pets.create_pet import CreatePetRequest
from app.schemas.pets.update_pet import UpdatePetRequest
from app.services.pet_service import PetService
from app.utils.pagination import PaginationParams
from app.utils.response import success_response

router = APIRouter(prefix="/pets", tags=["Pets"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_pet(
    payload: CreatePetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await PetService(db).create_pet(current_user.id, payload.model_dump())
    return success_response(data=data, message="Mascota registrada correctamente.", status_code=201)


@router.get("")
async def list_my_pets(
    params: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await PetService(db).list_pets(current_user.id, params)
    return success_response(data=data, message="Mascotas obtenidas correctamente.")


@router.get("/{pet_id}")
async def get_my_pet(
    pet_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await PetService(db).get_pet(pet_id, current_user.id)
    return success_response(data=data, message="Mascota obtenida correctamente.")


@router.patch("/{pet_id}")
async def update_my_pet(
    pet_id: UUID,
    payload: UpdatePetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await PetService(db).update_pet(pet_id, current_user.id, payload.model_dump())
    return success_response(data=data, message="Mascota actualizada correctamente.")


@router.delete("/{pet_id}")
async def delete_my_pet(
    pet_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await PetService(db).delete_pet(pet_id, current_user.id)
    return success_response(message="Mascota eliminada correctamente.")


@router.post("/{pet_id}/images", status_code=status.HTTP_201_CREATED)
async def upload_pet_image(
    pet_id: UUID,
    file: UploadFile = File(...),
    is_primary: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await PetService(db).get_pet(pet_id, current_user.id)  # valida ownership (404 si no es tuya)
    data = await ImageService(db).upload(ImageEntityType.PET, pet_id, current_user.id, file, is_primary)
    return success_response(data=data, message="Imagen subida correctamente.", status_code=201)


@router.get("/{pet_id}/images")
async def list_pet_images(pet_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await ImageService(db).list_for_entity(ImageEntityType.PET, pet_id)
    return success_response(data=data, message="Imágenes obtenidas correctamente.")


@router.delete("/{pet_id}/images/{image_id}")
async def delete_pet_image(
    pet_id: UUID,
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await PetService(db).get_pet(pet_id, current_user.id)
    await ImageService(db).delete(image_id, ImageEntityType.PET, pet_id)
    return success_response(message="Imagen eliminada correctamente.")