from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.auth.router import router as auth_router
from app.core.exception_handlers import register_exception_handlers
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

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

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