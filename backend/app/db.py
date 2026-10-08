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
    """Allow multiple AI-review revisions in an existing PostgreSQL database."""
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
            replaced_unique_index = False

            for constraint in inspector.get_unique_constraints(table_name):
                if constraint["column_names"] != [column_name] or not constraint["name"]:
                    continue
                connection.exec_driver_sql(
                    f"ALTER TABLE {quote(table_name)} "
                    f"DROP CONSTRAINT IF EXISTS {quote(constraint['name'])}"
                )
                replaced_unique_index = True

            for index in inspector.get_indexes(table_name):
                if (
                    index.get("column_names") != [column_name]
                    or not index.get("unique")
                    or not index.get("name")
                ):
                    continue
                connection.exec_driver_sql(
                    f"DROP INDEX IF EXISTS {quote(index['name'])}"
                )
                replaced_unique_index = True

            if replaced_unique_index:
                index_name = f"ix_{table_name}_{column_name}"
                connection.exec_driver_sql(
                    f"CREATE INDEX IF NOT EXISTS {quote(index_name)} "
                    f"ON {quote(table_name)} ({quote(column_name)})"
                )


def remove_legacy_confidence_threshold_columns(engine: Engine) -> None:
    """Drop obsolete configurable confidence thresholds from existing databases."""
    inspector = inspect(engine)
    tables = {
        "assessment_rule_configurations": ("confidence_threshold",),
        "assessment_rule_changes": (
            "old_confidence_threshold",
            "new_confidence_threshold",
        ),
        "damage_analysis_rule_snapshots": ("confidence_threshold",),
    }
    existing_tables = set(inspector.get_table_names())
    quote = engine.dialect.identifier_preparer.quote

    with engine.begin() as connection:
        for table_name, obsolete_columns in tables.items():
            if table_name not in existing_tables:
                continue
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name in obsolete_columns:
                if column_name not in columns:
                    continue
                connection.exec_driver_sql(
                    f"ALTER TABLE {quote(table_name)} DROP COLUMN {quote(column_name)}"
                )


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def ping_database(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.scalar(select(1)) == 1
