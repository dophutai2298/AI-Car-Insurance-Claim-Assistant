from collections.abc import Iterator
import base64
import hashlib
import hmac
import struct
import time

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


def totp(secret: str) -> str:
    key = base64.b32decode(secret)
    counter = int(time.time()) // 30
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{value:06d}"


def test_seeded_admin_can_log_in_and_read_session(client: TestClient):
    response = login(client, "admin@example.com", "Admin123!")

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["refresh_token"]
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


def admin_headers(client: TestClient) -> dict[str, str]:
    token = login(client, "admin@example.com", "Admin123!").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_an_adjuster_account(client: TestClient):
    response = client.post(
        "/api/auth/users",
        headers=admin_headers(client),
        json={
            "email": "assistant1",
            "full_name": "Assistant One",
            "password": "123456",
            "role": "ADJUSTER",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "email": "assistant1",
        "full_name": "Assistant One",
        "role": "ADJUSTER",
    }
    assert login(client, "assistant1", "123456").status_code == 200


def test_adjuster_cannot_create_accounts(client: TestClient):
    token = login(client, "adjuster@example.com", "Adjuster123!").json()["access_token"]

    response = client.post(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "assistant1", "password": "123456", "role": "ADJUSTER"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin access required"}


def test_duplicate_account_creation_returns_conflict(client: TestClient):
    payload = {"email": "assistant1", "password": "123456", "role": "ADJUSTER"}

    assert client.post("/api/auth/users", headers=admin_headers(client), json=payload).status_code == 201
    response = client.post("/api/auth/users", headers=admin_headers(client), json=payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "A user with this email already exists"}


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


def test_refresh_token_rotates_and_reuse_revokes_family(client: TestClient):
    signed_in = login(client, "adjuster@example.com", "Adjuster123!").json()
    first_refresh = signed_in["refresh_token"]

    rotated = client.post("/api/auth/refresh", json={"refresh_token": first_refresh})

    assert rotated.status_code == 200
    second_refresh = rotated.json()["refresh_token"]
    assert second_refresh != first_refresh
    assert client.post("/api/auth/refresh", json={"refresh_token": first_refresh}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": second_refresh}).status_code == 401


def test_logout_revokes_refresh_session(client: TestClient):
    refresh_token = login(client, "adjuster@example.com", "Adjuster123!").json()["refresh_token"]

    response = client.post("/api/auth/logout", json={"refresh_token": refresh_token})

    assert response.status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": refresh_token}).status_code == 401


def test_password_change_invalidates_existing_access_and_refresh_tokens(client: TestClient):
    signed_in = login(client, "adjuster@example.com", "Adjuster123!").json()
    old_headers = {"Authorization": f"Bearer {signed_in['access_token']}"}

    updated = client.patch(
        "/api/auth/users/adjuster@example.com",
        headers=admin_headers(client),
        json={"password": "NewAdjuster123!"},
    )

    assert updated.status_code == 200
    assert client.get("/api/auth/me", headers=old_headers).status_code == 401
    assert client.post(
        "/api/auth/refresh", json={"refresh_token": signed_in["refresh_token"]}
    ).status_code == 401
    assert login(client, "adjuster@example.com", "NewAdjuster123!").status_code == 200


def test_login_rate_limit_is_shared_database_state(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT_ATTEMPTS", "2")
    monkeypatch.setenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60")
    get_settings.cache_clear()

    assert login(client, "limited@example.com", "wrong").status_code == 401
    assert login(client, "limited@example.com", "wrong").status_code == 401
    limited = login(client, "limited@example.com", "wrong")

    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0


def test_refresh_rate_limit_cannot_be_bypassed_with_different_tokens(
    client: TestClient, monkeypatch
):
    monkeypatch.setenv("AUTH_RATE_LIMIT_ATTEMPTS", "2")
    monkeypatch.setenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60")
    get_settings.cache_clear()

    assert client.post(
        "/api/auth/refresh", json={"refresh_token": "a" * 32}
    ).status_code == 401
    assert client.post(
        "/api/auth/refresh", json={"refresh_token": "b" * 32}
    ).status_code == 401
    limited = client.post(
        "/api/auth/refresh", json={"refresh_token": "c" * 32}
    )

    assert limited.status_code == 429


def test_mfa_enrollment_challenge_and_one_time_recovery_code(client: TestClient):
    signed_in = login(client, "adjuster@example.com", "Adjuster123!").json()
    headers = {"Authorization": f"Bearer {signed_in['access_token']}"}
    secret = "JBSWY3DPEHPK3PXP"

    enrolled = client.post(
        "/api/auth/mfa/enroll",
        headers=headers,
        json={"secret": secret, "code": totp(secret)},
    )

    assert enrolled.status_code == 200
    assert "secret" not in enrolled.text.lower()
    recovery_code = enrolled.json()["recovery_codes"][0]

    challenge = login(client, "adjuster@example.com", "Adjuster123!")
    assert challenge.status_code == 200
    assert challenge.json()["mfa_required"] is True
    assert challenge.json()["access_token"] is None

    completed = client.post(
        "/api/auth/mfa/challenge",
        json={
            "challenge_token": challenge.json()["mfa_challenge_token"],
            "recovery_code": recovery_code,
        },
    )
    assert completed.status_code == 200
    assert completed.json()["access_token"]

    replay = client.post(
        "/api/auth/mfa/challenge",
        json={
            "challenge_token": login(
                client, "adjuster@example.com", "Adjuster123!"
            ).json()["mfa_challenge_token"],
            "recovery_code": recovery_code,
        },
    )
    assert replay.status_code == 401
