## AI Car Insurance Claim Assistant
- Description: An intelligent copilot that empowers insurance adjusters to optimize the auto claim workflow through automated document verification, damage assessment, and risk analysis.

## Local Development

### Prerequisites

- Python 3.10+
- Node.js 20.19+ or 22.12+
- Docker Desktop or another Docker-compatible runtime

### 1. Configure environment

Copy `.env.example` to `.env` and adjust values if needed. The defaults run the PoC in mock mode for the damage model, part search, and LLM.

To use Together AI through its OpenAI-compatible endpoint, keep `LLM_MODE=openai` and configure the following values in `.env`:

```text
LLM_BASE_URL=https://api.together.xyz/v1
OPENAI_API_KEY=your-together-api-key
OPENAI_MODEL=meta-llama/Llama-3.3-70B-Instruct-Turbo-Free
```

The application uses the same adapter with OpenAI later: replace `LLM_BASE_URL` and `OPENAI_MODEL` with the OpenAI values. `URL_MODEL` remains supported for the current local configuration. Do not commit API keys.

### 2. Start Postgres

```bash
docker compose up -d postgres
```

If your Docker install exposes Compose as the legacy command:

```bash
docker-compose up -d postgres
```

### 3. Start the backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The health endpoint is available at `http://localhost:8000/api/health`.

The backend creates the required tables and seeds these local demo accounts on startup:

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@example.com` | `Admin123!` |
| Adjuster | `adjuster@example.com` | `Adjuster123!` |

Set the demo credentials before the first database startup through the corresponding values in `.env`.
To reseed changed credentials locally, recreate the development Postgres volume.
Authentication endpoints are available at `POST /api/auth/login` and `GET /api/auth/me`.

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
