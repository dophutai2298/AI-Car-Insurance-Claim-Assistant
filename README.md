# AI Car Insurance Claim Assistant

A full-stack proof of concept for managing auto insurance claims, from claim intake and evidence upload to document extraction, vehicle damage analysis, AI assistance, and human review.

**Languages:** English | [Tiếng Việt](README.vi.md)

## Project at a glance

- Role-based workflows for `ADMIN`, `ADJUSTER`, and customer `USER` accounts.
- React, TypeScript, Vite, HeroUI, and Tailwind CSS frontend.
- FastAPI backend with PostgreSQL and local evidence storage.
- DeepDoc-based document OCR, vehicle damage detection, and optional LangChain/OpenAI integration.
- AI output supports decisions; an authorized human adjuster makes the final claim decision.

## Requirements

- Python 3.10 or 3.11
- Node.js 20.19+ or 22.12+
- Docker Desktop or another Docker Compose-compatible runtime
- The private `deepdoc_vietocr` wheel and car damage model weights for the local AI integrations

## Start locally on one port

Run commands from the repository root unless a `cd` command changes directory.

Build the frontend once. FastAPI then serves the built UI and `/api` from the same origin, so normal local use only needs the backend server. Start PostgreSQL. Before installing backend requirements, download the private wheel from the [package download link](https://drive.google.com/file/d/1LBGigUwhSzncbh4uMpkq5kZzU1JETlQz/view?usp=sharing) and place it at `backend/package/deepdoc_vietocr-0.1.0-py3-none-any.whl`. Add the car damage model weights under `AI/models/` when using damage analysis.

```powershell
Copy-Item .env.example .env
docker compose up -d postgres

# Download the private wheel and place it at:
# backend/package/deepdoc_vietocr-0.1.0-py3-none-any.whl

Push-Location frontend
npm ci
npm run build
Pop-Location

Push-Location backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --reload-dir app
```

Open `http://localhost:8000` for the UI and API. Swagger is at `http://localhost:8000/docs`. Uvicorn uses port `8000` by default; pass `--port <port>` to use another port. In Docker Compose, `APP_PORT` (default `8000`) selects the host port. Use `npm run dev` only when actively developing the frontend and needing Vite hot reload.

### Docker deployment

The Docker image builds the frontend and serves it through FastAPI. Before building, place the private DeepDoc wheel at `backend/package/deepdoc_vietocr-0.1.0-py3-none-any.whl` using the [package download link](https://drive.google.com/file/d/1LBGigUwhSzncbh4uMpkq5kZzU1JETlQz/view?usp=sharing).

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Open `http://localhost:8000`. Set `APP_PORT` in `.env` to publish a different host port. PostgreSQL is also available on port `5432` for database tools. Run `docker compose down` to stop services while preserving database and upload data.

### Frontend development with Vite

For frontend hot reload, run `npm run dev` in `frontend/` while the backend runs separately. Vite is available at `http://localhost:5173` and uses `FRONTEND_ORIGIN` from `.env` for API access.

Configure demo account credentials in `.env` before the first backend startup. See [Project guide](backend/package/PROJECT_GUIDE.md) for runtime modes, environment settings, workflows, data, and maintenance commands. See [Third-party notices](backend/package/THIRD_PARTY_NOTICES.md) for package download and license information.

## Documentation

- [Project guide: configuration, workflows, pricing, permissions, migrations, and checks](backend/package/PROJECT_GUIDE.md)
- [Third-party notices and private package download](backend/package/THIRD_PARTY_NOTICES.md)
