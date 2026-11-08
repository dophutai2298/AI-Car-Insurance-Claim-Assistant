# Project Guide

Additional setup, runtime, workflow, and maintenance notes for the AI Car Insurance Claim Assistant. The root README files contain the short project overview and local startup instructions.

## 1. Environment and runtime modes

Copy `.env.example` to `.env` at the repository root. Keep secrets and local data out of source control.

| Setting | Supported values | Default | Purpose |
| --- | --- | --- | --- |
| `DAMAGE_MODEL_MODE` | `local` | `local` | Runs the local `AI/CarDamageDetector` with model weights. |
| `PART_SEARCH_MODE` | `mock`, `unavailable` | `mock` | Uses the PostgreSQL VND catalog or reports pricing unavailable. |
| `DOCUMENT_OCR_MODE` | `deepdoc`, `mock` | `deepdoc` | Uses DeepDoc OCR or deterministic demo OCR. |
| `LLM_MODE` | `mock`, `openai` | `mock` | Uses demo responses or LangChain with an OpenAI-compatible chat model. |

The example configuration uses the local damage detector; part search and the LLM use mock mode. Document OCR defaults to DeepDoc. Set `DOCUMENT_OCR_MODE=mock` for deterministic document demos or tests.

For real LLM calls, configure:

```dotenv
LLM_MODE=openai
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=your-supported-model
LLM_REQUEST_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=0
```

When `LLM_BASE_URL` is unset, the application uses the default OpenAI endpoint. Set it only for an OpenAI-compatible provider. The selected model must support the structured output expected by the application; model availability and behavior vary by provider.

Set `LLM_TOKEN_USAGE_LOG_ENABLED=true` to print provider-reported token usage for document extraction, field validation, and AI Review. Logs include the operation, model, token counts, and document type or claim number; they do not include OCR text, prompts, or model output. Token counts are unavailable when the provider returns no token metadata.

For controlled local debugging, `LLM_RAW_OUTPUT_LOG_ENABLED=true` prints the raw AI Review JSON before parsing and persistence. This output can contain personal and claim information; keep this option disabled outside controlled local development.

The damage detector stores annotated vehicle images under `UPLOAD_ROOT/<claim>/annotations/`. Relevant settings include `DAMAGE_PART_MODEL_PATH`, `DAMAGE_MODEL_PATH`, `DAMAGE_OUTPUT_DIR`, `DAMAGE_PART_CONF`, `DAMAGE_DAMAGE_CONF`, `DAMAGE_MIN_PERCENT`, `DAMAGE_IMAGE_SIZE`, and `DAMAGE_DEVICE`. Default paths resolve from the repository root. Run its standalone smoke test from the repository root:

```powershell
python backend/scripts/test_car_damage_detector.py
```

## 2. Demo accounts and API endpoints

The backend creates missing tables and seeds configured demo users and vehicle manufacturers at startup. Existing users are not overwritten when environment credentials change. Set `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADJUSTER_EMAIL`, and `ADJUSTER_PASSWORD` in `.env` before the first startup to choose demo credentials. Change an existing account password through an approved account administration or database procedure.

The configured API base address is `http://localhost:8000`:

- Health check: `GET /api/health`
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI schema: `/openapi.json`

PostgreSQL listens on port `5432` in the default local setup. Connection and container credentials are defined in `.env.example`; override them in `.env` as needed.

## 3. Vehicle pricing catalog and Step 4

Startup creates the catalog and snapshot tables and seeds example prices for Toyota Camry 2022, Toyota Vios 2023, and BMW M3 2024. Repair and replacement prices are separate records, matched by exact make, model, year, part, and price category. Part identifiers normalize case, spaces, and hyphens only. Missing exact matches remain unavailable.

To seed a broader mock catalog, run from `backend`:

```powershell
python scripts/seed_price_catalog.py
```

The script covers 19 makes and the models listed in its source, from 2015 through the current year. It creates separate repair and replacement records for 21 detector part labels and four historical part identifiers for each make/model/year combination. These generated combinations and prices are demo data, not verified production years or market prices.

Edit `VEHICLES` (models and multipliers), `PART_PRICES_VND` (base repair/replacement amounts), and `PRICE_OVERRIDES` (exact make/model/year/part prices) in the script. Generated prices apply the model multiplier and a 3% annual adjustment relative to 2024, with the year multiplier capped between 60% and 120%; explicit overrides bypass both factors.

Options:

- `--dry-run` previews coverage without connecting to the database.
- `--make Toyota --start-year 2020 --end-year 2026` limits the selected make and year range.
- Existing catalog prices are preserved by default. `--update-existing` overwrites them and replaces their source metadata with the script's mock source.

The script reads `DATABASE_URL` from the project `.env` and commits all changes in one transaction.

Each Analysis stores an immutable price snapshot; catalog changes affect later runs only. Historical USD snapshots remain readable, while new VND amounts use whole-dong integers.

Step 4 presents the assessment, repair/replacement summaries, and a per-part price/provenance table. If some prices are missing, the UI labels the sum of available items as a known subtotal rather than a complete estimate. Mock prices are informational and exclude unmodeled labor, materials, taxes, and workshop fees. They do not determine payouts or replace the adjuster's decision.

AI Review receives the saved pricing snapshot in its existing LLM request. Its `price_recommendation` contains `recommendation` (`SUPPORTS_REPAIR`, `SUPPORTS_REPLACEMENT`, or `MANUAL_REVIEW`) and a concise `rationale`. If either repair or replacement pricing is missing, pricing requires manual review while the rest of the review remains available. Advice that conflicts with the deterministic damage assessment also requires manual review. Displayed amounts always come from Analysis; the AI does not calculate prices. Mock or unavailable AI pricing advice remains manual.

The Vietnamese translation includes the rationale and preserves the recommendation code. Historical reviews without pricing advice remain readable; rerunning AI Review creates a new revision from the saved Analysis snapshot. Prompt/schema versions: `ai-review-v3-pricing` / `ai-review-schema-v3-pricing`; translation versions: `ai-review-translation-vi-v2-pricing` / `ai-review-translation-schema-v2-pricing`.

## 4. Damage assessment thresholds

Admins configure the interpretation of model detections on **Assessment rules**. Thresholds apply to each detected vehicle part, not to the percentage of the whole vehicle that is damaged. Defaults are 40% repair maximum and 60% replacement minimum.

- If every detected part is at or below the repair maximum, the assessment is **Repair likely**.
- If any detected part reaches or exceeds the replacement minimum, the assessment is **Replacement likely**. `broken_component` and `severe_deformation` also trigger this result regardless of percentage.
- Values between the thresholds result in **Manual inspection required**.

With defaults, 35% can support repair, 50% needs manual inspection, and 65% supports replacement. Admins can change these global values; each analysis stores the values used for that run. These rules support review and do not make a final insurance decision.

## 5. Step 4 analysis completeness score

Step 4 runs only after Step 3 has saved a ready analysis snapshot. Step 3 blocks **Save All** if a required document analysis failed, a required value is missing, or a comparable document value is `MISMATCH` or cannot be checked. Correct the data and complete Step 3 before running AI Review. A mismatch is a workflow gate, not a score deduction.

The **Analysis completeness score** is deterministic. The LLM does not generate it, and it is not the probability that a claim is valid or approved. Each eligible review starts at 100 and subtracts 5 for each warning in the saved analysis snapshot, with a minimum of 0:

```text
score = max(0, 100 - (warnings * 5))
```

Examples: zero warnings = 100; one = 95; two = 90; twenty or more = 0. A required document with status `FAILED` is blocked by Step 3 and does not become a score deduction.

Warnings in a ready snapshot reduce the score and should prompt inspection of the related analysis. The score does not evaluate document matches, damage severity, LLM review text, or an adjuster's decision. LLM fallback does not itself change the score. Historical reviews retain their persisted scores. This is a limited processing signal and does not replace Step 3's match requirement or human review.

## 6. Access rules

- `ADMIN` can use all protected APIs, manage claims and configuration, and create customer `USER` accounts through Admin Config.
- `USER` can create and edit only their own Draft claims through Claim Information and Evidence & documents. After submitting a complete Draft, the user can see its identifier, creation date, and status in My Claims. Users cannot delete claims or access staff workflows and configuration.
- `ADJUSTER` can see submitted customer claims in the work queue and run Analysis, AI Review, and Human Review. Adjusters cannot open an unsubmitted customer Draft, change evidence, create claims or accounts, or manage configuration.

## 7. Automated checks

Backend checks, run from `backend`:

```powershell
pytest
python scripts/check_health.py
python scripts/check_database.py
```

Frontend checks, run from `frontend`:

```powershell
npm test
npm run build
```

`check_database.py` requires a reachable PostgreSQL instance configured through `DATABASE_URL`.

## 8. Legacy document field migration

Stop all backend processes and deploy the updated code before running the migration. Check the row count in each database and use the count reported by `--check` as the expected count:

```powershell
cd backend
python scripts/migrate_legacy_document_analysis_fields.py --check
python scripts/migrate_legacy_document_analysis_fields.py --apply --expected-legacy-rows COUNT_FROM_CHECK
python scripts/migrate_legacy_document_analysis_fields.py --check
```

Replace `COUNT_FROM_CHECK` with the count reported by the first command for that database. The migration verifies the expected row count and drops `document_analysis_fields` in one PostgreSQL transaction. If historical rows exist, it copies them to `legacy_document_analysis_fields_archive` and verifies the copy first; an empty table needs no archive. The application does not read the archive, and its rows are deleted automatically with the parent document analysis when a claim is deleted.

To restore the old schema and remaining archived rows, run:

```powershell
python scripts/migrate_legacy_document_analysis_fields.py --rollback
```

Rollback cannot restore claims deleted after the migration. Application startup and `create_all` do not automatically drop the old table.

## 9. Local files and database data

- Uploaded evidence is stored under `UPLOAD_ROOT` (default: `uploads` at the repository root).
- PostgreSQL data is stored in the Docker Compose volume `postgres-data`.
- The DeepDoc wheel is private and must be downloaded separately; do not commit it.
- Keep `.env`, uploaded evidence, and other sensitive data out of source control.
- 