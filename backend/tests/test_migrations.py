from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.db import run_database_migrations


BACKEND_DIR = Path(__file__).resolve().parents[1]


def migration_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def test_fresh_database_upgrades_and_downgrades(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    config = migration_config(database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    assert {"users", "claims", "workflow_analysis_runs"}.issubset(
        set(inspect(engine).get_table_names())
    )

    command.downgrade(config, "dd4475f105f2")
    inspector = inspect(engine)
    conclusion_index = next(
        index
        for index in inspector.get_indexes("copilot_conclusions")
        if index["name"] == "ix_copilot_conclusions_analysis_id"
    )
    review_index = next(
        index
        for index in inspector.get_indexes("workflow_ai_reviews")
        if index["name"] == "ix_workflow_ai_reviews_analysis_run_id"
    )
    assert conclusion_index["unique"] == 1
    assert review_index["unique"] == 1

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()


def test_programmatic_migration_uses_configured_database(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'programmatic.db').as_posix()}"

    run_database_migrations(database_url)

    engine = create_engine(database_url)
    assert "alembic_version" in inspect(engine).get_table_names()
    engine.dispose()


def test_existing_pre_alembic_database_is_stamped_then_upgraded(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}"
    config = migration_config(database_url)
    command.upgrade(config, "dd4475f105f2")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE alembic_version"))
    engine.dispose()

    run_database_migrations(database_url)

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert "assigned_adjuster_user_id" in {
        column["name"] for column in inspector.get_columns("claims")
    }
    assert "workflow_jobs" in inspector.get_table_names()
    engine.dispose()
