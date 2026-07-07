from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.catalog_service import CatalogService
from app.utils.response import success_response

router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("/species")
async def list_species(db: AsyncSession = Depends(get_db)):
    data = await CatalogService(db).list_species()
    return success_response(data=data, message="Especies obtenidas correctamente.")


@router.get("/species/{species_id}/breeds")
async def list_breeds(species_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await CatalogService(db).list_breeds(species_id)
    return success_response(data=data, message="Razas obtenidas correctamente.")