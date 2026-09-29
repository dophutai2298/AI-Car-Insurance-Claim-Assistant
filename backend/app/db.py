from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def create_database_engine(settings: Settings | None = None) -> Engine:
    current_settings = settings or get_settings()
    connect_args = {"check_same_thread": False} if current_settings.database_url.startswith("sqlite") else {}
    return create_engine(current_settings.database_url, connect_args=connect_args, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def upgrade_legacy_ai_review_constraints(engine: Engine) -> None:
    """Allow multiple AI-review revisions for an existing PostgreSQL development database."""
    if engine.dialect.name != "postgresql":
        return

    inspector = inspect(engine)
    targets = {
        "copilot_conclusions": "analysis_id",
        "workflow_ai_reviews": "analysis_run_id",
    }
    quote = engine.dialect.identifier_preparer.quote

    with engine.begin() as connection:
        for table_name, column_name in targets.items():
            for constraint in inspector.get_unique_constraints(table_name):
                if constraint["column_names"] != [column_name] or not constraint["name"]:
                    continue
                connection.exec_driver_sql(
                    f"ALTER TABLE {quote(table_name)} "
                    f"DROP CONSTRAINT IF EXISTS {quote(constraint['name'])}"
                )


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def ping_database(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.scalar(select(1)) == 1
