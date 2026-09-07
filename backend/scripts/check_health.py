import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def main() -> None:
    os.environ.setdefault("CHECK_DATABASE_ON_HEALTH", "false")
    get_settings.cache_clear()

    client = TestClient(create_app())
    try:
        response = client.get("/api/health")
        response.raise_for_status()
        payload = response.json()
    finally:
        client.close()

    assert payload["status"] == "ok"
    assert payload["service"] == "ai-car-claim-assistant-api"
    assert payload["runtime"]["damage_model_mode"] == "mock"
    assert payload["runtime"]["part_search_mode"] == "mock"
    assert payload["runtime"]["llm_mode"] == "mock"


if __name__ == "__main__":
    main()
