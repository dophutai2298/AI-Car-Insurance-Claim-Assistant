from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db import create_database_engine, ping_database


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health_check() -> dict[str, object]:
        database_status = "not_checked"

        if settings.check_database_on_health:
            try:
                database_status = "ok" if ping_database(create_database_engine(settings)) else "unavailable"
            except Exception:
                database_status = "unavailable"

        return {
            "status": "ok",
            "service": "ai-car-claim-assistant-api",
            "database": {"status": database_status},
            "runtime": settings.public_runtime(),
        }

    @app.get("/api/runtime-config")
    def runtime_config() -> dict[str, str]:
        return settings.public_runtime()

    return app


app = create_app()
