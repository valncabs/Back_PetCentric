"""Configuración central de logging.

Se usa el módulo estándar `logging`: un único handler en consola con formato
estructurado (timestamp, nivel, logger, mensaje). El nivel se lee de
`settings.LOG_LEVEL`. Los loggers del framework se ajustan para no saturar
(uvicorn/access se controlan desde la CLI de uvicorn).
"""
import logging
import sys

from app.core.config import settings

_LOGGING_CONFIGURED = False


def setup_logging() -> None:
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)

    # Silencia el trazado interno de librerías de bajo nivel.
    for noisy in ("uvicorn.access", "httpx", "asyncpg", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _LOGGING_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
