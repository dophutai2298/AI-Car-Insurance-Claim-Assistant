from collections.abc import Iterator
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import Request
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings, get_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
BASELINE_REVISION = "dd4475f105f2"


class Base(DeclarativeBase):
    pass


def create_database_engine(settings: Settings | None = None) -> Engine:
    current_settings = settings or get_settings()
    connect_args = {"check_same_thread": False} if current_settings.database_url.startswith("sqlite") else {}
    return create_engine(current_settings.database_url, connect_args=connect_args, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def run_database_migrations(database_url: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {},
    )
    try:
        table_names = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    legacy_schema_markers = {"users", "claims", "workflow_analysis_runs"}
    if "alembic_version" not in table_names and legacy_schema_markers.issubset(
        table_names
    ):
        command.stamp(config, BASELINE_REVISION)
    command.upgrade(config, "head")


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def ping_database(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.scalar(select(1)) == 1
