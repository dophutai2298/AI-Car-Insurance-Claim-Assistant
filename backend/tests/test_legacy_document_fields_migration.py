import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, inspect, text

from scripts.migrate_legacy_document_analysis_fields import (
    apply_migration,
    rollback_migration,
    table_state,
)


@pytest.fixture
def engine(tmp_path):
    database = create_engine(f"sqlite:///{(tmp_path / 'legacy-fields.db').as_posix()}")
    Table("document_analyses", MetaData(), Column("id", Integer, primary_key=True)).create(database)
    yield database
    database.dispose()


def add_legacy_fields(engine, *, with_row: bool) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE document_analysis_fields ("
            "id INTEGER PRIMARY KEY, document_analysis_id INTEGER NOT NULL, "
            "key VARCHAR(80) NOT NULL, label VARCHAR(120) NOT NULL, "
            "original_ai_value TEXT NOT NULL, reviewed_value TEXT NOT NULL, "
            "confidence FLOAT NOT NULL, status VARCHAR(7) NOT NULL, "
            "FOREIGN KEY(document_analysis_id) REFERENCES document_analyses(id))"
        )
        if with_row:
            connection.exec_driver_sql("INSERT INTO document_analyses (id) VALUES (1)")
            connection.exec_driver_sql(
                "INSERT INTO document_analysis_fields "
                "(id, document_analysis_id, key, label, original_ai_value, "
                "reviewed_value, confidence, status) "
                "VALUES (7, 1, 'full_name', 'Full name', 'Old value', "
                "'Reviewed value', 0.9, 'VALID')"
            )


@pytest.mark.parametrize("with_row", [False, True])
def test_migration_archives_and_restores_legacy_fields(engine, with_row):
    add_legacy_fields(engine, with_row=with_row)
    expected = 1 if with_row else 0

    assert apply_migration(engine, expected_rows=expected) == expected
    with engine.connect() as connection:
        assert table_state(connection) == (None, expected if with_row else None)
        assert inspect(connection).has_table("document_analyses")
        if with_row:
            assert inspect(connection).get_foreign_keys("legacy_document_analysis_fields_archive")[0]["options"]["ondelete"] == "CASCADE"
    assert apply_migration(engine, expected_rows=0) == 0

    assert rollback_migration(engine) == expected
    with engine.connect() as connection:
        assert table_state(connection) == (expected, None)
        if with_row:
            assert connection.scalar(
                text("SELECT reviewed_value FROM document_analysis_fields WHERE id = 7")
            ) == "Reviewed value"


def test_migration_requires_the_audited_row_count(engine):
    add_legacy_fields(engine, with_row=True)

    with pytest.raises(RuntimeError, match="row count changed"):
        apply_migration(engine, expected_rows=0)

    with engine.connect() as connection:
        assert table_state(connection) == (1, None)


def test_archive_fields_are_removed_when_the_parent_analysis_is_deleted(engine):
    add_legacy_fields(engine, with_row=True)
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    apply_migration(engine, expected_rows=1)
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM document_analyses WHERE id = 1")

    with engine.connect() as connection:
        assert table_state(connection) == (None, 0)
    assert rollback_migration(engine) == 0
