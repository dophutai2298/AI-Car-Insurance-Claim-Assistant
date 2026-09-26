## AI Car Insurance Claim Assistant
- Description: An intelligent copilot that empowers insurance adjusters to optimize the auto claim workflow through automated document verification, damage assessment, and risk analysis.

## Local Development

### Prerequisites

- Python 3.9 to 3.11
- Node.js 20.19+ or 22.12+
- Docker Desktop or another Docker-compatible runtime

### 1. Configure environment

Copy `.env.example` to `.env` and adjust values if needed. The defaults run the PoC in mock mode for the damage model, part search, and LLM.

Vehicle damage analysis supports `DAMAGE_MODEL_MODE=mock` for deterministic demos
and `DAMAGE_MODEL_MODE=local` for the local `damage_car` package boundary. The
local package's public inference API is still a focused TODO; until it is wired,
local mode reports an unavailable model instead of fabricating results. No damage
model URL is required because this integration runs in the backend process.

Document OCR defaults to the locally installed `deepdoc_vietocr` package. Set
`DOCUMENT_OCR_MODE=mock` only for deterministic local demos and automated tests.

To use OpenAI, set `LLM_MODE=openai` and configure the following values in `.env`:

```text
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5.6-luna
LLM_REQUEST_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=0
LLM_TOKEN_USAGE_LOG_ENABLED=true
```

Do not set `LLM_BASE_URL` for the official OpenAI API; LangChain uses its default
OpenAI endpoint. `LLM_BASE_URL` is reserved for an explicitly configured,
OpenAI-compatible provider. The legacy `URL_MODEL` variable is not supported.
Use a fixed model with structured-output support for document extraction. Dynamic
router models can vary in latency and schema support between requests. The timeout
and retry settings keep one failed document from blocking the remaining workflow.
Do not commit API keys.

Set `LLM_TOKEN_USAGE_LOG_ENABLED=true` to print provider-reported token usage after
each document extraction, document field-validation, and AI Review LLM call. Each
terminal log includes the operation, relevant document type or claim number, model,
input tokens, output tokens, and total tokens. Set it to `false` to disable these logs.
OCR text, prompts, and model output are never included in the token-usage log. If the
provider omits usage metadata, the log reports `status=unavailable` instead of
estimating tokens with a potentially incompatible tokenizer.

### 2. Start Postgres

```bash
docker compose up -d postgres
```

If your Docker install exposes Compose as the legacy command:

```bash
docker-compose up -d postgres
```

### 3. Start the backend

Download the private `deepdoc_vietocr-0.1.0-py3-none-any.whl` package from
[Google Drive](https://drive.google.com/file/d/1LBGigUwhSzncbh4uMpkq5kZzU1JETlQz/view?usp=sharing)
and place it in `backend/package/` before installing the backend requirements.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The health endpoint is available at `http://localhost:8000/api/health`.
- Interactive Swagger UI is available at `http://localhost:8000/docs`, 
- with the OpenAPI schema at `http://localhost:8000/openapi.json`. 
- ReDoc: `http://localhost:8000/redoc`

The backend creates the required tables and seeds these local demo accounts on startup:

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@example.com` | `Admin123!` |
| Adjuster | `adjuster@example.com` | `Adjuster123!` |

Set the demo credentials before the first database startup through the corresponding values in `.env`.
To reseed changed credentials locally, recreate the development Postgres volume.
Authentication endpoints are available at `POST /api/auth/login` and `GET /api/auth/me`.

`ADMIN` can use all protected APIs. `ADJUSTER` can run Analysis, AI Review, and Human
Review, and can read its own session, a claim detail, and its evidence content to
support those workflows. Claim creation/listing, evidence changes, account management,
and configuration require `ADMIN`. An admin must prepare a claim before an adjuster
opens its detail URL; the current dashboard claim list is admin-only.

### DeepDoc Vietnamese document analysis

This project can use the local `deepdoc_vietocr` package for CPU-optimized document
processing. DeepDoc supports text OCR, document layout detection, and table
structure extraction. It integrates VietOCR and ONNX to improve Vietnamese text
recognition and is designed to be reusable in document-processing and RAG systems.

The wheel is distributed privately and is intentionally not committed to Git.
Download `deepdoc_vietocr-0.1.0-py3-none-any.whl` from
[here](https://drive.google.com/file/d/1LBGigUwhSzncbh4uMpkq5kZzU1JETlQz/view?usp=sharing)
and place it in `backend/package/`.

Install the downloaded wheel in the backend virtual environment:

```bash
cd backend
pip install package/deepdoc_vietocr-0.1.0-py3-none-any.whl
```

Example usage:

```python
from deepdoc_vietocr import DocumentReader

reader = DocumentReader()
result = reader.extract("sample.pdf")

print(result.text)
print(result.markdown)

layouts = reader.detect_layout("sample.pdf")
tables = reader.extract_tables("sample.pdf")
```

`result.text` contains the extracted text, while `result.markdown` preserves a
more structured representation. `detect_layout` returns document layout data and
`extract_tables` returns detected table structures.

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

### Automated checks

```bash
cd backend
pytest
python scripts/check_health.py
python scripts/check_database.py

cd ../frontend
npm test
npm run build
```
### Third-party licenses

`deepdoc_vietocr` contains components derived from DeepDoc/RAGFlow and VietOCR,
which are distributed under the Apache License 2.0.

See [`THIRD_PARTY_NOTICES.md`](./backend/package/THIRD_PARTY_NOTICES.md) for attribution and
third-party license information.
