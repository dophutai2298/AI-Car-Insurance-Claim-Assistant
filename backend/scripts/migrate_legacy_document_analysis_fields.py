"""Retire the mock document field table after archiving its historical rows."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import Column, Float, ForeignKey, Integer, MetaData, String, Table, Text, inspect, text
from sqlalchemy.engine import Connection, Engine

from app.core.config import get_settings
from app.db import create_database_engine

LEGACY_TABLE = "document_analysis_fields"
ARCHIVE_TABLE = "legacy_document_analysis_fields_archive"
COLUMNS = (
    "id",
    "document_analysis_id",
    "key",
    "label",
    "original_ai_value",
    "reviewed_value",
    "confidence",
    "status",
)


def create_field_table(connection: Connection, name: str, *, cascade_delete: bool) -> None:
    metadata = MetaData()
    Table("document_analyses", metadata, autoload_with=connection)
    table = Table(
        name,
        metadata,
        Column("id", Integer, primary_key=True),
        Column(
            "document_analysis_id",
            Integer,
            ForeignKey("document_analyses.id", ondelete="CASCADE" if cascade_delete else None),
            index=True,
            nullable=False,
        ),
        Column("key", String(80), nullable=False),
        Column("label", String(120), nullable=False),
        Column("original_ai_value", Text, nullable=False),
        Column("reviewed_value", Text, nullable=False),
        Column("confidence", Float, nullable=False),
        Column("status", String(7), nullable=False),
    )
    table.create(connection)


def table_state(connection: Connection) -> tuple[int | None, int | None]:
    inspector = inspect(connection)
    legacy_count = (
        connection.scalar(text(f"SELECT count(*) FROM {LEGACY_TABLE}"))
        if inspector.has_table(LEGACY_TABLE)
        else None
    )
    archive_count = (
        connection.scalar(text(f"SELECT count(*) FROM {ARCHIVE_TABLE}"))
        if inspector.has_table(ARCHIVE_TABLE)
        else None
    )
    return legacy_count, archive_count


def apply_migration(engine: Engine, *, expected_rows: int) -> int:
    if expected_rows < 0:
        raise ValueError("Expected row count cannot be negative")
    with engine.begin() as connection:
        legacy_count, archive_count = table_state(connection)
        if legacy_count is None:
            if expected_rows == 0:
                return 0
            raise RuntimeError("Legacy table is absent; expected row count does not match")
        if archive_count is not None:
            raise RuntimeError("Both legacy and archive tables exist; inspect them before migrating")
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql(f"LOCK TABLE {LEGACY_TABLE} IN ACCESS EXCLUSIVE MODE")
            legacy_count, _ = table_state(connection)
        if legacy_count != expected_rows:
            raise RuntimeError(
                f"Legacy row count changed: expected {expected_rows}, found {legacy_count}"
            )
        if legacy_count == 0:
            connection.exec_driver_sql(f"DROP TABLE {LEGACY_TABLE}")
            return 0
        if not inspect(connection).has_table("document_analyses"):
            raise RuntimeError("Cannot archive legacy fields without document_analyses")
        create_field_table(connection, ARCHIVE_TABLE, cascade_delete=True)
        columns = ", ".join(COLUMNS)
        connection.exec_driver_sql(
            f"INSERT INTO {ARCHIVE_TABLE} ({columns}) SELECT {columns} FROM {LEGACY_TABLE}"
        )
        archived_count = connection.scalar(text(f"SELECT count(*) FROM {ARCHIVE_TABLE}"))
        if archived_count != legacy_count:
            raise RuntimeError("Legacy document field archive row count does not match")
        connection.exec_driver_sql(f"DROP TABLE {LEGACY_TABLE}")
        return archived_count or 0


def rollback_migration(engine: Engine) -> int:
    with engine.begin() as connection:
        legacy_count, archive_count = table_state(connection)
        if legacy_count is not None:
            if archive_count is not None:
                raise RuntimeError("Both legacy and archive tables exist; inspect them before rollback")
            return legacy_count
        if not inspect(connection).has_table("document_analyses"):
            raise RuntimeError("Cannot restore legacy fields without document_analyses")
        if archive_count is None:
            create_field_table(connection, LEGACY_TABLE, cascade_delete=False)
            return 0
        orphan_count = connection.scalar(
            text(
                f"SELECT count(*) FROM {ARCHIVE_TABLE} AS archived "
                "LEFT JOIN document_analyses AS document "
                "ON document.id = archived.document_analysis_id "
                "WHERE document.id IS NULL"
            )
        )
        if orphan_count:
            raise RuntimeError(
                f"Cannot restore {orphan_count} archived fields: their document analyses no longer exist"
            )

        create_field_table(connection, LEGACY_TABLE, cascade_delete=False)
        columns = ", ".join(COLUMNS)
        connection.exec_driver_sql(
            f"INSERT INTO {LEGACY_TABLE} ({columns}) SELECT {columns} FROM {ARCHIVE_TABLE}"
        )
        restored_count = connection.scalar(text(f"SELECT count(*) FROM {LEGACY_TABLE}"))
        if restored_count != archive_count:
            raise RuntimeError("Restored legacy document field row count does not match archive")
        if restored_count and connection.dialect.name == "postgresql":
            connection.exec_driver_sql(
                "SELECT setval(pg_get_serial_sequence('document_analysis_fields', 'id'), "
                "(SELECT max(id) FROM document_analysis_fields), true)"
            )
        connection.exec_driver_sql(f"DROP TABLE {ARCHIVE_TABLE}")
        return restored_count or 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Show row counts without changing the database")
    action.add_argument("--apply", action="store_true", help="Archive rows and drop the legacy table")
    action.add_argument("--rollback", action="store_true", help="Restore the table from its archive")
    parser.add_argument(
        "--expected-legacy-rows", type=int, help="Row count observed with --check; required for --apply"
    )
    args = parser.parse_args()
    if args.apply and args.expected_legacy_rows is None:
        parser.error("--apply requires --expected-legacy-rows from a prior --check")

    engine = create_database_engine(get_settings())
    try:
        if args.check:
            with engine.connect() as connection:
                legacy_count, archive_count = table_state(connection)
            print(f"legacy_rows={legacy_count} archive_rows={archive_count}")
        elif args.apply:
            print(
                f"archived_rows={apply_migration(engine, expected_rows=args.expected_legacy_rows)} "
                "legacy_table_dropped=true"
            )
        else:
            print(f"restored_rows={rollback_migration(engine)}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
