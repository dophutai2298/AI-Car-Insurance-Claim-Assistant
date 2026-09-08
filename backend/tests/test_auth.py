from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    database_path = tmp_path / "auth-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-long-enough-for-auth-tests")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "Admin123!")
    monkeypatch.setenv("ADJUSTER_EMAIL", "adjuster@example.com")
    monkeypatch.setenv("ADJUSTER_PASSWORD", "Adjuster123!")
    monkeypatch.setenv("CHECK_DATABASE_ON_HEALTH", "false")
    get_settings.cache_clear()

    with TestClient(create_app()) as test_client:
        yield test_client

    get_settings.cache_clear()


def login(client: TestClient, email: str, password: str):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_seeded_admin_can_log_in_and_read_session(client: TestClient):
    response = login(client, "admin@example.com", "Admin123!")

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"] == {
        "email": "admin@example.com",
        "full_name": "Demo Admin",
        "role": "ADMIN",
    }

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json() == payload["user"]


def test_seeded_adjuster_receives_adjuster_role(client: TestClient):
    response = login(client, "adjuster@example.com", "Adjuster123!")

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "ADJUSTER"


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("admin@example.com", "wrong-password"),
        ("missing@example.com", "wrong-password"),
    ],
)
def test_invalid_credentials_return_the_same_safe_error(
    client: TestClient, email: str, password: str
):
    response = login(client, email, password)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer invalid-token"},
    ],
)
def test_authenticated_route_rejects_missing_or_invalid_token(client: TestClient, headers):
    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401


def test_adjuster_cannot_access_admin_route(client: TestClient):
    adjuster_token = login(client, "adjuster@example.com", "Adjuster123!").json()["access_token"]

    forbidden_response = client.get(
        "/api/admin/access-check",
        headers={"Authorization": f"Bearer {adjuster_token}"},
    )

    assert forbidden_response.status_code == 403
    assert forbidden_response.json() == {"detail": "Admin access required"}


def test_admin_can_access_admin_route(client: TestClient):
    admin_token = login(client, "admin@example.com", "Admin123!").json()["access_token"]

    response = client.get(
        "/api/admin/access-check",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "role": "ADMIN"}
