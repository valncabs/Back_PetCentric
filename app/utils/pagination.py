from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PaginationParams:
    """Dependencia común para listados grandes: page, page_size, search, sort, order.
    FastAPI la resuelve automáticamente vía Depends() gracias a los Query() en __init__."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Número de página, empieza en 1."),
        page_size: int = Query(20, ge=1, le=100, description="Tamaño de página, máx 100."),
        search: str | None = Query(None, description="Texto de búsqueda."),
        sort: str | None = Query(None, description="Campo por el cual ordenar."),
        order: str = Query("asc", pattern="^(asc|desc)$", description="Dirección: asc o desc."),
    ) -> None:
        self.page = page
        self.page_size = page_size
        self.search = search
        self.sort = sort
        self.order = order

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResult(BaseModel, Generic[T]):
    """Solo para referencia/documentación de forma; el service arma el dict
    directamente con paginate(), no es obligatorio instanciar esta clase."""
    items: list[T]
    page: int
    page_size: int
    total: int
    pages: int


async def paginate(
    db: AsyncSession,
    stmt: Select,
    params: PaginationParams,
    serializer,
) -> dict[str, Any]:
    """Ejecuta un SELECT ya filtrado por el repository, aplicando conteo total
    y paginación. `serializer` transforma cada fila del resultado en un dict.

    Devuelve el contrato estándar de paginación:
    {items, page, page_size, total, pages}
    """
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    paged_stmt = stmt.offset(params.offset).limit(params.page_size)
    rows = (await db.execute(paged_stmt)).scalars().all()

    pages = (total + params.page_size - 1) // params.page_size if total > 0 else 0

    return {
        "items": [serializer(row) for row in rows],
        "page": params.page,
        "page_size": params.page_size,
        "total": total,
        "pages": pages,
    }