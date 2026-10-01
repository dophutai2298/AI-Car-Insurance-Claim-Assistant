"""Print read-only persistence statistics for the claim-analysis data audit."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import sys

from sqlalchemy import MetaData, Table, case, func, select
from sqlalchemy.engine import Engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.db import create_database_engine


AUDIT_TABLES = (
    "users",
    "vehicle_manufacturers",
    "assessment_rule_configurations",
    "assessment_rule_changes",
    "claims",
    "evidence",
    "other_document_groups",
    "other_document_group_evidence",
    "evidence_removals",
    "claim_incidents",
    "workflow_analysis_runs",
    "workflow_analysis_damage",
    "document_analyses",
    "document_analysis_fields",
    "document_ocr_results",
    "document_extraction_results",
    "document_extracted_fields",
    "document_field_validations",
    "claim_consistency_checks",
    "damage_analyses",
    "damage_detections",
    "damage_model_outputs",
    "damage_analysis_rule_snapshots",
    "reference_part_prices",
    "confirmed_analysis_snapshots",
    "copilot_conclusions",
    "copilot_review_outputs",
    "workflow_ai_reviews",
    "copilot_conclusion_reviews",
    "copilot_conclusion_review_reversions",
)

DISTRIBUTION_COLUMNS = {
    "claims": ("status",),
    "workflow_analysis_runs": ("status", "damage_status"),
    "document_analyses": ("document_type", "status", "warnings_json"),
    "document_ocr_results": ("document_type", "status"),
    "document_extraction_results": ("document_type", "status"),
    "document_field_validations": ("status",),
    "claim_consistency_checks": ("status",),
    "damage_analyses": ("assessment",),
    "damage_detections": ("status",),
    "copilot_conclusions": ("status",),
    "workflow_ai_reviews": ("review_status", "warnings_json"),
    "copilot_conclusion_reviews": ("status",),
    "confirmed_analysis_snapshots": ("status",),
}

NULL_COUNTS = {
    "document_ocr_results": ("raw_text", "warning", "adapter_name"),
    "document_extraction_results": ("warning",),
    "document_extracted_fields": ("ai_extracted_value", "confirmed_value"),
    "damage_analyses": ("warning",),
    "reference_part_prices": ("amount", "failure_reason"),
    "copilot_conclusions": ("fallback_summary", "failure_reason", "provider_model"),
}


def _load_tables(engine: Engine, names: Iterable[str]) -> dict[str, Table]:
    metadata = MetaData()
    return {
        name: Table(name, metadata, autoload_with=engine)
        for name in names
    }


def main() -> None:
    engine = create_database_engine(get_settings())
    try:
        tables = _load_tables(engine, AUDIT_TABLES)
        with engine.connect() as connection:
            print("# Schema inventory")
            for name, table in tables.items():
                columns = ", ".join(
                    f"{column.name}:{column.type}"
                    f"{' nullable' if column.nullable else ' required'}"
                    for column in table.columns
                )
                print(f"- {name}: {columns}")

            print()
            print("# Persistence row counts")
            print("| Table | Rows |")
            print("| --- | ---: |")
            for name, table in tables.items():
                row_count = connection.scalar(select(func.count()).select_from(table))
                print(f"| {name} | {row_count} |")

            print("\n# Selected value distributions")
            for table_name, column_names in DISTRIBUTION_COLUMNS.items():
                table = tables[table_name]
                for column_name in column_names:
                    column = table.c[column_name]
                    rows = connection.execute(
                        select(column, func.count())
                        .group_by(column)
                        .order_by(func.count().desc(), column)
                    )
                    values = ", ".join(
                        f"{value!r}={count}" for value, count in rows
                    )
                    print(f"- {table_name}.{column_name}: {values or '(no rows)'}")

            print("\n# Selected null counts")
            for table_name, column_names in NULL_COUNTS.items():
                table = tables[table_name]
                row_count = connection.scalar(select(func.count()).select_from(table))
                for column_name in column_names:
                    column = table.c[column_name]
                    null_count = connection.scalar(
                        select(func.sum(case((column.is_(None), 1), else_=0))).select_from(table)
                    )
                    print(
                        f"- {table_name}.{column_name}: "
                        f"null={null_count or 0}, non_null={(row_count or 0) - (null_count or 0)}"
                    )

            conclusions = tables["copilot_conclusions"]
            equal_fallbacks = connection.scalar(
                select(func.count())
                .select_from(conclusions)
                .where(
                    conclusions.c.fallback_summary.is_not(None),
                    conclusions.c.summary == conclusions.c.fallback_summary,
                )
            )
            print("\n# Candidate overlap checks")
            print(
                "- copilot_conclusions rows where summary equals fallback_summary: "
                f"{equal_fallbacks}"
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
