"""Migración manual: agrega token_version a la tabla users.

Idempotente. Ejecutar desde Backend_ con el entorno activo:

    python -m app.scripts.migrate_user_token_version

El esquema no se gestiona con alembic, por eso se aplica este ALTER de
forma explícita. token_version se incrementa al cambiar/restablecer la
contraseña para invalidar los access tokens emitidos con un valor anterior.
"""
import asyncio

from sqlalchemy import text

from app.core.database import engine


ALTER_COLUMN = text("""
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0
""")


async def main() -> None:
    async with engine.begin() as conn:
        await conn.execute(ALTER_COLUMN)
    print("OK: columna token_version agregada a users (default 0).")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
