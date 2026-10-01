# Backend claim-analysis persistence audit

Audit date: 2026-10-01

This audit covers the FastAPI/PostgreSQL persistence used by claim intake,
evidence, document OCR and extraction, damage analysis, AI Review, Human Review,
and administrator configuration. The goal is one authoritative source for each
current business fact without erasing provenance or historical state.

## Method

- Inspected every SQLAlchemy model and the repository/service that writes it.
- Traced API response assembly, frontend readers, tests, and startup schema code.
- Queried the current development PostgreSQL database with the read-only
  `backend/scripts/audit_persistence.py` script. The script prints every table,
  column type/nullability, row count, and selected candidate distributions.
- Classified apparent overlap as canonical state, immutable history/provenance,
  a deliberate projection, a removable duplicate, or deferred pending a safe
  expand-contract migration.

The current backend has no Alembic baseline. Startup still calls
`Base.metadata.create_all()` and contains one ad-hoc legacy constraint upgrade.
Task 23 therefore blocks destructive contract/drop migrations, but not this
audit or compatible expand-phase changes.

## Current database sample

The inspected database contains 22 claims and 22 analysis runs. Relevant row
counts are:

| Area | Tables and row counts |
| --- | --- |
| Access/configuration | `users` 6; rule configuration 1; rule changes 0; vehicle manufacturers 19 |
| Evidence | `evidence` 14; groups 0; group links 0; `evidence_removals` 7; `claim_incidents` 2 |
| Workflow | `workflow_analysis_runs` 22; run/damage links 21 |
| Document summary | `document_analyses` 88; `document_analysis_fields` 0 |
| OCR and extraction | `document_ocr_results` 88; `document_extraction_results` 88; `document_extracted_fields` 308 |
| Legacy document validation | `document_field_validations` 0; `claim_consistency_checks` 0 |
| Damage | `damage_analyses` 21; `damage_detections` 62; `damage_model_outputs` 21; rule snapshots 21 |
| Confirmed state | `confirmed_analysis_snapshots` 14 |
| AI Review | `copilot_conclusions` 20; `copilot_review_outputs` 20; `workflow_ai_reviews` 20 |
| Human Review | reviews 0; review reversions 0 |

All 88 current document analyses, OCR results, and extraction results are
completed. All document-analysis warnings are empty in this sample. The absence
of rows in legacy document field tables is evidence about this database only;
their code paths remain active in mock mode and their API shapes are tested.

Twelve AI conclusions are unavailable/fallback results. In all 12 rows,
`fallback_summary` exactly equals `summary`. All 20 workflow AI reviews have the
constant `REVIEW_REQUIRED` status.

## Persistence inventory

| Persistence area | Columns and responsibility | Main writers | Main readers | Decision |
| --- | --- | --- | --- | --- |
| `users` | Identity, credential hash, role, active flag | Auth seeding/account services | Authentication and authorization | Keep as canonical account state. |
| `vehicle_manufacturers` | Manufacturer name and active flag | Admin manufacturer service | Claim validation and admin API/UI | Keep as canonical configuration. |
| Assessment rule configuration/change | Current threshold values and immutable old/new audit values | Assessment rule service/repository | Damage assessment and admin history | Keep both current state and audit history. |
| `claims` | Current claimant, vehicle, lifecycle status, creator and timestamps | Claim repository/workflow services | Dashboard, APIs, authorization and analysis | Keep. `status` is an intentional query projection, not analysis-run history. |
| Evidence/group/removal tables | Canonical file metadata, optional grouping, and removal tombstone | Evidence repository/storage | Upload/content APIs, analysis, UI and snapshots | Keep. Removal history and generated annotation evidence are provenance. |
| `claim_incidents` | Current incident facts and input revision | Incident repository | Analysis input and AI Review context | Keep. Revision gates stale analysis. |
| Workflow runs and damage link | Per-run lifecycle, input revision, failure state and run-to-damage identity | Analysis workflow/repository | Polling, claim detail, snapshots and reruns | Keep as analysis history. The link is the run/analysis identity, not redundant with claim ownership. |
| Confirmed analysis snapshots | Immutable confirmed payload, revision and readiness | Snapshot service/repository | AI Review gate and curated AI input | Keep unchanged. This intentionally duplicates mutable source tables at confirmation time. |
| Document category analyses | Per-run/category aggregate status and warnings | Document pipeline | Run completion, API/UI and snapshot warnings | Keep as a deliberate category projection. |
| Document analysis fields | Mock document fields and edits | Mock document pipeline and legacy edit endpoint | API/UI compatibility and tests | Defer removal. Zero current rows do not prove no supported mock/dev consumers. |
| OCR results | Per-run/evidence raw OCR, adapter provenance, metadata, status and warning | Document pipeline/repository | Reuse logic, extraction, API/UI and tests | Keep raw OCR and provenance. Filename/content-type copies are deferred candidates. |
| Extraction results/fields | Structured AI extraction, confirmed values, source IDs, status and prompt/schema versions | Extraction pipeline/repository | Confirmation UI, snapshots, AI Review context and tests | Keep as canonical AI-extracted and human-confirmed document state. |
| Field validations/consistency checks | Legacy validation output and comparison-at-time facts | Legacy validation branch and edit endpoint | API/UI compatibility and tests | Defer removal until the legacy branch and response contract are explicitly retired. |
| Damage analyses/detections | Assessment summary and normalized per-part operational rows | Damage workflow/repository | Rules, prices, snapshots, API table and AI Review | Keep as canonical operational damage facts. |
| Damage model outputs | Adapter identity, complete model JSON and model warnings | Damage repository | Image/part rendering, snapshot provenance and API | Keep as model provenance. It contains nested damage types and annotation mapping not represented by detection rows. |
| Damage rule snapshots/prices | Rules and reference-price result used at analysis time | Damage repository | API, snapshot and AI Review | Keep immutable analysis-time facts. |
| Copilot conclusions | Revision status, recommendation, summary, failure/provider metadata | AI Review repository | Claim response and Human Review | Keep `summary` as the canonical readable conclusion. Stop persisting duplicate fallback text. |
| Copilot structured outputs | Full structured review plus prompt/schema versions | AI Review repository | API/UI and Human Review context | Keep. Summary is an indexed/readable projection of this versioned provider output. |
| Workflow AI reviews | Run/conclusion link, score, review-state projection, warnings and evidence references | AI Review workflow | Claim response/UI | Keep per-revision context. Constant `review_status` is a future contract candidate. |
| Human reviews/reversions | Adjuster decision and immutable reversion audit | Human Review repository | Claim lifecycle and history UI | Keep as decision history. |

## Field-level decisions

### Consolidated now: AI fallback summary

`copilot_conclusions.summary` and `fallback_summary` contained the same text for
every fallback/unavailable row in the inspected database. Before this change,
the LLM service created both values, the repository persisted both, and the
claim response read both. The frontend only consumes the API field and does not
require two persisted copies.

The compatible expand phase is complete:

- `summary` is the sole source of truth in the service and for new database rows.
- New fallback/unavailable conclusions leave the legacy nullable column empty.
- The API still returns `fallback_summary = summary` for `FALLBACK` and
  `LLM_UNAVAILABLE`, preserving the external contract and UI behavior.
- Existing duplicated values remain untouched. Dropping/backfilling the legacy
  column is deferred until Task 23 supplies Alembic.

### Deferred: legacy document field tables

`document_analysis_fields`, `document_field_validations`, and
`claim_consistency_checks` have no rows in the current database, while the newer
extraction tables contain the active confirmed data. They are not yet safe to
drop: mock OCR mode still writes document-analysis fields, edit endpoints and
response schemas still expose them, the frontend renders validation results,
and backend/frontend tests exercise those contracts. Retirement requires an
explicit compatibility decision and an expand-contract migration.

### Deferred: repeated document identity/version columns

OCR filename/content type can currently be reached through `evidence`, and some
extracted-field run/source/version columns can be reached through their parent
extraction. They are actively used by direct queries, reuse logic, API response
assembly, snapshots, and tests. They also preserve what was processed and under
which prompt/schema. Keep them until a migration demonstrates equivalent
historical reads and bounded query behavior.

### Retained: JSON plus normalized damage rows

`damage_model_outputs.output_json` and `damage_detections` overlap on part,
damage type, and percentage, but they have different responsibilities. The JSON
is the complete adapter result with nested damage types and annotated-evidence
mapping; detections are normalized operational facts used by assessment,
pricing, responses, and AI Review. Neither can currently reconstruct the other
without losing information or changing behavior.

### Retained: snapshots, warnings, statuses and evidence references

- Confirmed snapshot JSON is immutable input history, not a cache of current rows.
- Model, assessment, document-category, workflow, and AI Review warnings belong
  to different processing scopes and are read independently.
- Claim, run, per-result, conclusion, and Human Review statuses represent
  different state machines.
- Snapshot evidence references record confirmation input; workflow AI Review
  references record what a specific conclusion reviewed.
- AI validity percentage is stored per conclusion revision so reruns remain
  explainable even if calculation rules change.

`workflow_ai_reviews.review_status` is currently constant and may be derivable,
but it is part of the API/UI contract and non-null schema. It remains a contract
candidate after Alembic is available; it is not removed in this audit.

## Migration frontier

After Task 23 establishes Alembic, the safe contract order is:

1. Verify all deployed writers leave `copilot_conclusions.fallback_summary` null
   and all readers derive the compatibility field from status plus `summary`.
2. Re-run the persistence audit against a representative upgraded database and
   check external/reporting consumers, not only this repository.
3. Drop `fallback_summary` in a versioned migration and verify upgrade,
   downgrade where supported, AI fallback, rerun, and historical claim detail.
4. Treat legacy document tables and constant workflow status as separate future
   decisions; do not bundle them into the fallback-summary contract migration.

No historical rows, OCR text, extracted or confirmed values, snapshots, source
evidence, prompt/schema versions, damage model output, or review revisions were
deleted by this task.

## Verification

- Backend: `155 passed`; one existing Starlette/AnyIO deprecation warning.
- Frontend production build: passed, with the existing large-chunk warning.
- Frontend tests: 22 passed and 3 existing `App.test.tsx` login/language tests
  failed. No frontend file changed in this task; claim workflow and table tests
  involved in this persistence contract passed.
