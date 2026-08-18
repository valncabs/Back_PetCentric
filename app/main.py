from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.auth.router import router as auth_router
from app.core.exception_handlers import register_exception_handlers
from app.api.profile.router import router as profile_router
from app.api.pets.router import router as pets_router
from app.api.catalog.router import router as catalog_router
from app.api.rbac.router import router as rbac_router
from app.api.lost_reports.router import router as lost_reports_router
from app.api.found_reports.router import router as found_reports_router
from app.api.admin_users.router import router as admin_users_router
from app.api.admin_reports.router import router as admin_reports_router
from app.api.messaging.router import router as messaging_router
from app.api.notifications.router import router as notifications_router
from app.api.chat.router import router as chat_router

setup_logging()
_log = logging.getLogger("app.access")


def _cors_origins() -> list[str]:
    """Orígenes permitidos desde CORS_ALLOWED_ORIGINS (CSV); si no se definen,
    se usa FRONTEND_URL como único origen permitido."""
    configured = [
        origin.strip()
        for origin in settings.CORS_ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ]
    if configured:
        return configured
    return [settings.FRONTEND_URL]


def _api_docs_enabled() -> bool:
    """La documentación (/docs, /redoc, /openapi.json) se expone en todos los
    entornos, incluida producción."""
    return True

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    docs_url="/docs" if _api_docs_enabled() else None,
    redoc_url="/redoc" if _api_docs_enabled() else None,
    openapi_url="/openapi.json" if _api_docs_enabled() else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
    ],
)

register_exception_handlers(app)


@app.middleware("http")
async def log_requests(request, call_next):
    """Registra cada petición HTTP con método, ruta, IP, status y duración."""
    start = time.perf_counter()
    status = "?"
    try:
        response = await call_next(request)
        status = response.status_code
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        _log.info(
            "%s %s -> %s [%.1fms]",
            request.method,
            request.url.path,
            status,
            elapsed_ms,
        )
    return response


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(pets_router)
app.include_router(catalog_router)
app.include_router(rbac_router)
app.include_router(lost_reports_router)
app.include_router(found_reports_router)
app.include_router(admin_users_router)
app.include_router(admin_reports_router)
app.include_router(messaging_router)
app.include_router(notifications_router)
app.include_router(chat_router)