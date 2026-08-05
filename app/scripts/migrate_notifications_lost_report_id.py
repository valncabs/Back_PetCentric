"""Migración manual: agrega lost_report_id a la tabla notifications.

Idempotente. Ejecutar desde Backend_ con el entorno activo:

    python -m app.scripts.migrate_notifications_lost_report_id

El esquema no se gestiona con alembic, por eso se aplica este ALTER de
forma explícita. Se enlaza la notificación FOUND_MATCH con el reporte de
pérdida para que la app abra el modal de avistamientos correspondiente.
"""
import asyncio

from sqlalchemy import text

from app.core.database import engine


ALTER_COLUMN = text("""
    ALTER TABLE notifications
        ADD COLUMN IF NOT EXISTS lost_report_id UUID
""")

ALTER_FK = text("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'fk_notifications_lost_report'
        ) THEN
            ALTER TABLE notifications
                ADD CONSTRAINT fk_notifications_lost_report
                FOREIGN KEY (lost_report_id) REFERENCES lost_reports(id) ON DELETE SET NULL;
        END IF;
    END $$
""")

CREATE_INDEX = text("""
    CREATE INDEX IF NOT EXISTS ix_notifications_lost_report_id
        ON notifications (lost_report_id)
""")


async def main() -> None:
    async with engine.begin() as conn:
        await conn.execute(ALTER_COLUMN)
        await conn.execute(ALTER_FK)
        await conn.execute(CREATE_INDEX)
    print("OK: columna lost_report_id agregada a notifications.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
