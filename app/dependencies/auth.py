from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user import UserRepository

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise UnauthorizedException("Token inválido o expirado.") from exc

    if payload.get("type") != "access":
        raise UnauthorizedException("Token inválido.")

    user = await UserRepository(db).get_by_id(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedException("Usuario no encontrado o inactivo.")
    return user