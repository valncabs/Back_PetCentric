"""Registro dinámico de la URL del proxy de herramientas (mcpo).

La URL del quick tunnel de cloudflared es efímera y cambia en cada arranque
de iniciar.sh, por lo que no puede vivir solo en una env var estática.
Este módulo guarda la URL más reciente en memoria y, best effort, la persiste
en la tabla `settings` de la BD para que sobreviva a los redeploys de Render.
"""
import logging
import uuid

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine

_log = logging.getLogger(__name__)

PROXY_URL_SETTING_KEY = "ai_tool_proxy_url"

_override: str | None = None


def get_proxy_url() -> str:
    """URL efectiva: el valor dinámico si existe, si no el de settings."""
    return (_override or settings.AI_TOOL_PROXY_URL).rstrip("/")


async def load_persisted_proxy_url() -> None:
    """Carga el último valor persistido desde la BD (best effort)."""
    global _override
    if _override:
        return
    try:
        async with engine.begin() as conn:
            row = (
                await conn.execute(
                    text("SELECT value FROM settings WHERE key = :k"),
                    {"k": PROXY_URL_SETTING_KEY},
                )
            ).first()
        if row and row.value.startswith(("http://", "https://")):
            _override = row.value.rstrip("/")
            _log.info("Proxy de herramientas cargado desde BD: %s", _override)
    except Exception:
        _log.warning(
            "No se pudo leer la URL del proxy desde la BD; se usa el fallback estático. "
            "iniciar.sh la reportará de nuevo al arrancar.",
            exc_info=True,
        )


async def update_proxy_url(url: str, persist: bool = True) -> str:
    """Fija la URL dinámica actual y la persiste (best effort) en `settings`."""
    global _override
    url = url.rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"proxy_url inválida: {url!r}")

    _override = url
    _log.info("Proxy de herramientas actualizado en memoria: %s", url)

    if not persist:
        return url

    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO settings (id, key, value, description, updated_at)
                    VALUES (:id, :key, :value, :desc, now())
                    ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value,
                        description = EXCLUDED.description,
                        updated_at = now()
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "key": PROXY_URL_SETTING_KEY,
                    "value": url,
                    "desc": "Última URL del proxy de herramientas reportada por iniciar.sh",
                },
            )
        _log.info("Proxy de herramientas persistido en BD: %s", url)
    except Exception:
        _log.warning(
            "No se pudo persistir la URL del proxy en la BD; queda solo en memoria. "
            "Tras un redeploy volverá al fallback estático hasta que iniciar.sh la reporte de nuevo.",
            exc_info=True,
        )
    return url