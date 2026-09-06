from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine

from app.core.config import Settings, get_settings


def create_database_engine(settings: Settings | None = None) -> Engine:
    current_settings = settings or get_settings()
    return create_engine(current_settings.database_url, pool_pre_ping=True)


def ping_database(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.scalar(select(1)) == 1
