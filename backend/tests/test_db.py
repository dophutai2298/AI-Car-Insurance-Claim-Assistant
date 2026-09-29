from contextlib import AbstractContextManager
from typing import Any

import app.db as db_module


class _IdentifierPreparer:
    @staticmethod
    def quote(identifier: str) -> str:
        return f'"{identifier}"'


class _Dialect:
    name = "postgresql"
    identifier_preparer = _IdentifierPreparer()


class _Connection:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def exec_driver_sql(self, statement: str) -> None:
        self.statements.append(statement)


class _Transaction(AbstractContextManager[_Connection]):
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    def __enter__(self) -> _Connection:
        return self.connection

    def __exit__(self, *args: object) -> None:
        return None


class _Engine:
    dialect = _Dialect()

    def __init__(self) -> None:
        self.connection = _Connection()

    def begin(self) -> _Transaction:
        return _Transaction(self.connection)


class _Inspector:
    @staticmethod
    def get_unique_constraints(table_name: str) -> list[dict[str, Any]]:
        return []

    @staticmethod
    def get_indexes(table_name: str) -> list[dict[str, Any]]:
        if table_name == "copilot_conclusions":
            return [
                {
                    "name": "ix_copilot_conclusions_analysis_id",
                    "column_names": ["analysis_id"],
                    "unique": True,
                }
            ]
        return [
            {
                "name": "ix_workflow_ai_reviews_analysis_run_id",
                "column_names": ["analysis_run_id"],
                "unique": True,
            },
            {
                "name": "ix_workflow_ai_reviews_conclusion_id",
                "column_names": ["conclusion_id"],
                "unique": True,
            },
        ]


def test_upgrade_legacy_ai_review_constraints_replaces_unique_indexes(monkeypatch) -> None:
    engine = _Engine()
    monkeypatch.setattr(db_module, "inspect", lambda _engine: _Inspector())

    db_module.upgrade_legacy_ai_review_constraints(engine)  # type: ignore[arg-type]

    assert engine.connection.statements == [
        'DROP INDEX IF EXISTS "ix_copilot_conclusions_analysis_id"',
        'CREATE INDEX IF NOT EXISTS "ix_copilot_conclusions_analysis_id" '
        'ON "copilot_conclusions" ("analysis_id")',
        'DROP INDEX IF EXISTS "ix_workflow_ai_reviews_analysis_run_id"',
        'CREATE INDEX IF NOT EXISTS "ix_workflow_ai_reviews_analysis_run_id" '
        'ON "workflow_ai_reviews" ("analysis_run_id")',
    ]
