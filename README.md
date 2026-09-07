## AI Car Insurance Claim Assistant
- Description: An intelligent copilot that empowers insurance adjusters to optimize the auto claim workflow through automated document verification, damage assessment, and risk analysis.

## Local Development

### Prerequisites

- Python 3.10+
- Node.js 20.19+ or 22.12+
- Docker Desktop or another Docker-compatible runtime

### 1. Configure environment

Copy `.env.example` to `.env` and adjust values if needed. The defaults run the PoC in mock mode for the damage model, part search, and LLM.

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
npm run build
```
