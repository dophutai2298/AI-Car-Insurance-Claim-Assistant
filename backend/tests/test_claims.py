from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    database_path = tmp_path / "claims-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-long-enough-for-claim-tests")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "Admin123!")
    monkeypatch.setenv("ADJUSTER_EMAIL", "adjuster@example.com")
    monkeypatch.setenv("ADJUSTER_PASSWORD", "Adjuster123!")
    monkeypatch.setenv("CHECK_DATABASE_ON_HEALTH", "false")
    get_settings.cache_clear()

    with TestClient(create_app()) as test_client:
        yield test_client

    get_settings.cache_clear()


def adjuster_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": "adjuster@example.com", "password": "Adjuster123!"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_claim(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/claims",
        headers=adjuster_headers(client),
        json={
            "claimant_name": "Mai Nguyen",
            "vehicle": {
                "make": "Toyota",
                "model": "Camry",
                "year": 2022,
                "license_plate": "51H-123.45",
                "vin": "4T1G11AKXNU123456",
            },
        },
    )

    assert response.status_code == 201
    return response.json()


def test_adjuster_can_create_persisted_claim_case(client: TestClient):
    claim = create_claim(client)

    assert claim["id"] == "CLM-000001"
    assert claim["claimant_name"] == "Mai Nguyen"
    assert claim["vehicle"] == {
        "make": "Toyota",
        "model": "Camry",
        "year": 2022,
        "license_plate": "51H-123.45",
        "vin": "4T1G11AKXNU123456",
    }
    assert claim["status"] == "DRAFT"


def test_dashboard_lists_claim_summary_and_last_updated(client: TestClient):
    create_claim(client)

    response = client.get("/api/claims", headers=adjuster_headers(client))

    assert response.status_code == 200
    claims = response.json()
    assert len(claims) == 1
    assert claims[0]["id"] == "CLM-000001"
    assert claims[0]["claimant_name"] == "Mai Nguyen"
    assert claims[0]["vehicle_summary"] == "2022 Toyota Camry"
    assert claims[0]["status"] == "DRAFT"
    assert claims[0]["updated_at"]


def test_adjuster_can_open_claim_detail(client: TestClient):
    created_claim = create_claim(client)

    response = client.get(f"/api/claims/{created_claim['id']}", headers=adjuster_headers(client))

    assert response.status_code == 200
    assert response.json()["id"] == created_claim["id"]
    assert response.json()["vehicle"]["vin"] == "4T1G11AKXNU123456"
    assert response.json()["status"] == "DRAFT"


def test_unknown_claim_returns_not_found(client: TestClient):
    response = client.get("/api/claims/CLM-999999", headers=adjuster_headers(client))

    assert response.status_code == 404
    assert response.json() == {"detail": "Claim not found"}


def test_adjuster_can_move_claim_from_draft_to_analysis(client: TestClient):
    created_claim = create_claim(client)

    response = client.patch(
        f"/api/claims/{created_claim['id']}/status",
        headers=adjuster_headers(client),
        json={"status": "ANALYZING"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ANALYZING"


def test_claim_cannot_skip_safe_lifecycle_transition(client: TestClient):
    created_claim = create_claim(client)

    response = client.patch(
        f"/api/claims/{created_claim['id']}/status",
        headers=adjuster_headers(client),
        json={"status": "AI_APPROVED"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Invalid claim lifecycle transition"}
