from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, claims, vehicle_makes
from app.api.dependencies import require_admin
from app.core.config import get_settings
from app.db import Base, create_database_engine, create_session_factory, ping_database
from app.services.auth import seed_demo_users
from app.services.vehicle_manufacturers import seed_vehicle_manufacturers

OPENAPI_TAGS = [
    {"name": "auth", "description": "Session authentication and current-user operations."},
    {"name": "claims", "description": "Claim lifecycle, evidence, damage analysis, and copilot results."},
    {"name": "admin", "description": "Administrator-only assessment rule configuration."},
    {"name": "system", "description": "Service health and runtime configuration."},
]
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_database_engine(settings)
        Base.metadata.create_all(engine)
        app.state.session_factory = create_session_factory(engine)
        with app.state.session_factory() as session:
            seed_demo_users(session, settings)
            seed_vehicle_manufacturers(session)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        summary="Interactive API documentation for the insurance claim assistant PoC.",
        version="0.1.0",
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        swagger_ui_parameters={"docExpansion": "list", "displayRequestDuration": True},
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.exception("Unexpected API error for %s %s", request.method, request.url.path, exc_info=error)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(claims.router)
    app.include_router(vehicle_makes.router)

    @app.get("/api/health", tags=["system"])
    def health_check() -> dict[str, object]:
        database_status = "not_checked"

        if settings.check_database_on_health:
            try:
                engine = create_database_engine(settings)
                try:
                    database_status = "ok" if ping_database(engine) else "unavailable"
                finally:
                    engine.dispose()
            except Exception:
                database_status = "unavailable"

        return {
            "status": "ok",
            "service": "ai-car-claim-assistant-api",
            "database": {"status": database_status},
        }

    @app.get("/api/runtime-config", tags=["system"], dependencies=[Depends(require_admin)])
    def runtime_config() -> dict[str, str]:
        return settings.public_runtime()

    return app


app = create_app()
