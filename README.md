# AI Car Insurance Claim Assistant

A full-stack proof of concept for managing auto insurance claims. Adjusters can review claim information, evidence, OCR and structured document extraction, vehicle damage findings, AI recommendations, and human review decisions.

**Languages:** English | [Tiếng Việt](README.vi.md)

## What it does

- Provides role-based access for `ADMIN` and `ADJUSTER` users.
- Manages claims, vehicle and incident details, and evidence files.
- Runs document OCR and LLM-based extraction for identity cards, insurance policies, vehicle registrations, and driver licenses.
- Runs vehicle damage analysis and presents normalized damage findings by vehicle part.
- Supports AI review, human review, and configurable assessment rules.
- Stores application data in PostgreSQL and uploaded files under the configured local upload directory.

This is a decision-support PoC. AI findings and recommendations require review by an authorized human adjuster.

## Technology

- Frontend: React, TypeScript, Vite, HeroUI, Tailwind CSS, TanStack Query/Table, and Recharts.
- Backend: Python, FastAPI, SQLAlchemy, and Pydantic.
- Database: PostgreSQL.
- Document OCR: private `deepdoc_vietocr` package (DeepDoc, VietOCR, and ONNX).
- LLM: mock mode by default; optional OpenAI-compatible integration through LangChain.

## Prerequisites

- Python 3.10 or 3.11.
- Node.js 20.19+ or 22.12+.
- Docker Desktop or another Docker-compatible runtime with Compose.
- Access to the private `deepdoc_vietocr` wheel for real document OCR.
- An OpenAI API key only if using `LLM_MODE=openai`.

## Quick start

Commands below are run from the repository root unless a `cd` command changes directory.

### 1. Configure environment

```powershell
Copy-Item .env.example .env
```

The example config uses the local car-damage detector, while part search and the LLM remain in mock mode. Document OCR defaults to DeepDoc. For a deterministic document demo or tests, set `DOCUMENT_OCR_MODE=mock` in `.env`.

For real LLM calls, configure these values in `.env`:

```dotenv
LLM_MODE=openai
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=your-supported-model
LLM_REQUEST_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=0
```

The default OpenAI endpoint is used when `LLM_BASE_URL` is unset. Set `LLM_BASE_URL` only when using an OpenAI-compatible endpoint. Never commit API keys or other secrets.

To print provider-reported token usage for document extraction, field validation, and AI Review, set `LLM_TOKEN_USAGE_LOG_ENABLED=true`. Logs include operation, model, token counts, and the relevant document type or claim number; they do not include OCR text, prompts, or model output. If the provider supplies no token metadata, the log reports it as unavailable.

For local AI Review debugging, set `LLM_RAW_OUTPUT_LOG_ENABLED=true` to print the raw JSON returned by the model before parsing and persistence. This output can contain claim and personal information, so keep it disabled outside controlled local development.

### 2. Start PostgreSQL

```powershell
docker compose up -d postgres
```

PostgreSQL is exposed on port `5432`. The default local connection and container credentials are in `.env.example`; change them in `.env` before starting the application when needed.

### 3. Install and start the backend

The DeepDoc wheel is private and is not stored in Git. Download `deepdoc_vietocr-0.1.0-py3-none-any.whl` from [Google Drive](https://drive.google.com/file/d/1LBGigUwhSzncbh4uMpkq5kZzU1JETlQz/view?usp=sharing) and place it at `backend/package/deepdoc_vietocr-0.1.0-py3-none-any.whl` before installing requirements.

The backend requirements also install the detector dependencies from `AI/requirements.txt`. Keep the model weights at `AI/models/car_part.pt` and `AI/models/car_damage.pt` or configure their paths in `.env`.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --reload-dir app
```

If PowerShell blocks virtual environment activation, use the activation command appropriate for your shell or invoke `.venv\Scripts\python.exe` directly.

The API creates missing tables and seeds the configured demo users and vehicle manufacturers on startup. Existing users are not overwritten when environment credentials change. Configure credentials before the first startup. To change an existing account's password, use an approved database or account-administration procedure.

The example demo accounts are:

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@example.com` | `Admin123!` |
| Adjuster | `adjuster@example.com` | `Adjuster123!` |

Set `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADJUSTER_EMAIL`, and `ADJUSTER_PASSWORD` in `.env` before first startup to use different demo credentials.

The backend is available at `http://localhost:8000`:

- Health check: `GET /api/health`
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI schema: `/openapi.json`

### 4. Install and start the frontend

Open another terminal at the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Runtime modes

| Setting | Supported values | Default | Purpose |
| --- | --- | --- | --- |
| `DAMAGE_MODEL_MODE` | `local` | `local` | Runs the local `AI/CarDamageDetector` with the bundled model weights. |
| `PART_SEARCH_MODE` | `mock`, `unavailable` | `mock` | Demo reference prices or no price search results. |
| `DOCUMENT_OCR_MODE` | `deepdoc`, `mock` | `deepdoc` | DeepDoc OCR or deterministic demo OCR. |
| `LLM_MODE` | `mock`, `openai` | `mock` | Demo responses or LangChain calls to an OpenAI-compatible chat model. |

For the `openai` mode, set `OPENAI_API_KEY` and `OPENAI_MODEL`. The selected model must support the structured output expected by the application. Provider/model availability and response behavior may vary.

The detector reads each uploaded vehicle image and stores its annotated result under `UPLOAD_ROOT/<claim>/annotations/`. Configure `DAMAGE_PART_MODEL_PATH`, `DAMAGE_MODEL_PATH`, `DAMAGE_OUTPUT_DIR`, `DAMAGE_PART_CONF`, `DAMAGE_DAMAGE_CONF`, `DAMAGE_MIN_PERCENT`, `DAMAGE_IMAGE_SIZE`, and `DAMAGE_DEVICE` in `.env` as needed. The default paths resolve from the repository root. The standalone smoke test is `python backend/scripts/test_car_damage_detector.py`.

## Access rules

- `ADMIN` can use all protected APIs and manage claims and configuration, and can create user accounts.
- `ADJUSTER` can run Analysis, AI Review, and Human Review. Adjusters can also read claim details and evidence needed for those workflows; claim creation/listing, evidence changes, account management, and configuration are admin-only.

## DeepDoc package

The private `deepdoc_vietocr` package provides CPU-oriented text recognition, document layout detection, and table extraction, with VietOCR and ONNX support for Vietnamese OCR. The wheel is excluded from Git. Download it from the [project package link](https://drive.google.com/file/d/1LBGigUwhSzncbh4uMpkq5kZzU1JETlQz/view?usp=sharing) and put it in `backend/package/` before installing backend requirements.

Example API:

```python
from deepdoc_vietocr import DocumentReader

reader = DocumentReader()
result = reader.extract("sample.pdf")

print(result.text)
print(result.markdown)

layouts = reader.detect_layout("sample.pdf")
tables = reader.extract_tables("sample.pdf")
```

See [`backend/package/THIRD_PARTY_NOTICES.md`](backend/package/THIRD_PARTY_NOTICES.md) for package download details and third-party notices.

## Automated checks

Backend checks:

```powershell
cd backend
pytest
python scripts/check_health.py
python scripts/check_database.py
```

Frontend checks:

```powershell
cd frontend
npm test
npm run build
```

`check_database.py` requires a reachable PostgreSQL instance configured by `DATABASE_URL`.

## Local files and data

- Uploaded evidence is stored under `UPLOAD_ROOT` (default: `uploads` at the repository root).
- PostgreSQL data is stored in the Docker Compose volume `postgres-data`.
- The DeepDoc wheel is private and must be downloaded separately; do not commit it.
- Keep `.env`, uploaded evidence, and other sensitive data out of source control.

## License notices

See [`backend/package/THIRD_PARTY_NOTICES.md`](backend/package/THIRD_PARTY_NOTICES.md) for attribution and license information related to DeepDoc/RAGFlow, VietOCR, and the private package.
