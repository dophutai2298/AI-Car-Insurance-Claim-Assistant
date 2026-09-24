from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute

from app.core.config import get_settings
from app.main import create_app
from app.services.claims import ClaimService


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'security.db').as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-long-enough-for-security-tests")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "Admin123!")
    monkeypatch.setenv("ADJUSTER_EMAIL", "adjuster@example.com")
    monkeypatch.setenv("ADJUSTER_PASSWORD", "Adjuster123!")
    monkeypatch.setenv("UPLOAD_ROOT", str(tmp_path / "uploads"))
    monkeypatch.setenv("CHECK_DATABASE_ON_HEALTH", "false")
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("DOCUMENT_OCR_MODE", "mock")
    get_settings.cache_clear()
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
    get_settings.cache_clear()


def headers(client: TestClient, role: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": f"{role}@example.com", "password": "Admin123!" if role == "admin" else "Adjuster123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


PROTECTED_ROUTES = [
    ("GET", "/api/auth/me", True),
    ("POST", "/api/auth/users", False),
    ("GET", "/api/runtime-config", False),
    ("GET", "/api/vehicle-makes", False),
    ("GET", "/api/admin/access-check", False),
    ("GET", "/api/admin/assessment-rules", False),
    ("PUT", "/api/admin/assessment-rules", False),
    ("GET", "/api/admin/assessment-rules/history", False),
    ("GET", "/api/admin/vehicle-makes", False),
    ("POST", "/api/admin/vehicle-makes", False),
    ("PUT", "/api/admin/vehicle-makes/1", False),
    ("POST", "/api/claims", False),
    ("GET", "/api/claims", False),
    ("GET", "/api/claims/CLM-999999", True),
    ("PATCH", "/api/claims/CLM-999999/status", False),
    ("POST", "/api/claims/CLM-999999/evidence", False),
    ("DELETE", "/api/claims/CLM-999999/evidence/1", False),
    ("GET", "/api/claims/CLM-999999/evidence/1/content", True),
    ("PATCH", "/api/claims/CLM-999999/information", False),
    ("POST", "/api/claims/CLM-999999/damage-analysis", True),
    ("POST", "/api/claims/CLM-999999/analysis-runs", True),
    ("PATCH", "/api/claims/CLM-999999/document-analyses/1/fields/1", True),
    ("PATCH", "/api/claims/CLM-999999/analysis-runs/1/field-validations/1", True),
    ("PATCH", "/api/claims/CLM-999999/analysis-runs/1/extraction-fields/1", True),
    ("PUT", "/api/claims/CLM-999999/analysis-runs/1/extraction-fields", True),
    ("POST", "/api/claims/CLM-999999/analysis-runs/1/ai-review", True),
    ("POST", "/api/claims/CLM-999999/copilot-conclusions/1/review", True),
    ("POST", "/api/claims/CLM-999999/copilot-conclusions/1/review/revert", True),
]


def test_permission_matrix_covers_every_registered_api_route(client: TestClient):
    public = {("GET", "/api/health"), ("POST", "/api/auth/login")}
    for route in client.app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
            continue
        for method in route.methods:
            if (method, route.path) in public:
                continue
            assert any(
                candidate_method == method and route.path_regex.fullmatch(candidate_path)
                for candidate_method, candidate_path, _ in PROTECTED_ROUTES
            ), f"Unclassified API permission: {method} {route.path}"


@pytest.mark.parametrize("method,path,adjuster_allowed", PROTECTED_ROUTES)
def test_permission_matrix(client: TestClient, method: str, path: str, adjuster_allowed: bool):
    unauthenticated = client.request(method, path, json={} if method in {"POST", "PUT", "PATCH"} else None)
    invalid = client.request(method, path, headers={"Authorization": "Bearer invalid"}, json={} if method in {"POST", "PUT", "PATCH"} else None)
    assert unauthenticated.status_code == 401
    assert invalid.status_code == 401

    adjuster = client.request(method, path, headers=headers(client, "adjuster"), json={} if method in {"POST", "PUT", "PATCH"} else None)
    assert (adjuster.status_code not in {401, 403}) if adjuster_allowed else adjuster.status_code == 403

    admin = client.request(method, path, headers=headers(client, "admin"), json={} if method in {"POST", "PUT", "PATCH"} else None)
    assert admin.status_code not in {401, 403}


def test_public_health_is_minimal_and_runtime_config_is_admin_only(client: TestClient):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert "runtime" not in health.json()
    assert client.get("/api/runtime-config", headers=headers(client, "adjuster")).status_code == 403
    assert "damage_model_mode" in client.get("/api/runtime-config", headers=headers(client, "admin")).json()


def test_adjuster_can_restore_only_own_session_identity(client: TestClient):
    response = client.get("/api/auth/me", headers=headers(client, "adjuster"))
    assert response.status_code == 200
    assert response.json()["email"] == "adjuster@example.com"
    assert response.json()["role"] == "ADJUSTER"
    assert "password" not in response.json()


def test_upload_rejects_active_content_and_cleans_batch(client: TestClient, tmp_path):
    claim = client.post("/api/claims", headers=headers(client, "admin"), json={
        "claimant_name": "Mai Nguyen", "vehicle": {"make": "Toyota", "model": "Camry", "year": 2022}
    }).json()
    upload = client.post(
        f"/api/claims/{claim['id']}/evidence",
        headers=headers(client, "admin"),
        data={"categories": ["VEHICLE_DAMAGE_IMAGE", "ID_CARD"]},
        files=[
            ("files", ("car.jpg", b"\xff\xd8\xffimage", "image/jpeg")),
            ("files", ("identity.jpg", b"<script>alert(1)</script>", "image/jpeg")),
        ],
    )
    assert upload.status_code == 422
    assert client.get(f"/api/claims/{claim['id']}", headers=headers(client, "admin")).json()["evidence"] == []
    assert list((tmp_path / "uploads" / claim["id"]).glob("*")) == []


def test_evidence_download_uses_verified_type_and_nosniff(client: TestClient):
    claim = client.post("/api/claims", headers=headers(client, "admin"), json={
        "claimant_name": "Mai Nguyen", "vehicle": {"make": "Toyota", "model": "Camry", "year": 2022}
    }).json()
    uploaded = client.post(
        f"/api/claims/{claim['id']}/evidence", headers=headers(client, "admin"),
        data={"categories": ["INSURANCE_POLICY"]},
        files=[("files", ("policy.pdf", b"%PDF-1.4 document", "application/pdf"))],
    ).json()["evidence"][0]
    downloaded = client.get(uploaded["content_url"], headers=headers(client, "adjuster"))
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/octet-stream"
    assert downloaded.headers["content-disposition"].startswith("attachment;")
    assert downloaded.headers["x-content-type-options"] == "nosniff"


def test_upload_enforces_file_count_size_and_supported_media(client: TestClient, monkeypatch):
    claim = client.post("/api/claims", headers=headers(client, "admin"), json={
        "claimant_name": "Mai Nguyen", "vehicle": {"make": "Toyota", "model": "Camry", "year": 2022}
    }).json()
    path = f"/api/claims/{claim['id']}/evidence"
    admin = headers(client, "admin")

    too_many = client.post(
        path, headers=admin, data={"categories": ["ID_CARD"] * 11},
        files=[("files", (f"id-{index}.jpg", b"\xff\xd8\xffimage", "image/jpeg")) for index in range(11)],
    )
    assert too_many.status_code == 422

    active_content = client.post(
        path, headers=admin, data={"categories": ["ID_CARD"]},
        files=[("files", ("identity.svg", b"<svg onload='alert(1)'></svg>", "image/svg+xml"))],
    )
    assert active_content.status_code == 422

    mismatched_type = client.post(
        path, headers=admin, data={"categories": ["ID_CARD"]},
        files=[("files", ("identity.jpg", b"%PDF-1.4 document", "image/jpeg"))],
    )
    assert mismatched_type.status_code == 422

    monkeypatch.setenv("MAX_EVIDENCE_FILE_SIZE_BYTES", "8")
    get_settings.cache_clear()
    oversized = client.post(
        path, headers=admin, data={"categories": ["ID_CARD"]},
        files=[("files", ("identity.jpg", b"\xff\xd8\xff123456", "image/jpeg"))],
    )
    assert oversized.status_code == 422
    assert client.get(f"/api/claims/{claim['id']}", headers=admin).json()["evidence"] == []


def test_download_rechecks_stored_content_before_serving(client: TestClient, tmp_path):
    claim = client.post("/api/claims", headers=headers(client, "admin"), json={
        "claimant_name": "Mai Nguyen", "vehicle": {"make": "Toyota", "model": "Camry", "year": 2022}
    }).json()
    uploaded = client.post(
        f"/api/claims/{claim['id']}/evidence", headers=headers(client, "admin"),
        data={"categories": ["ID_CARD"]},
        files=[("files", ("identity.jpg", b"\xff\xd8\xffimage", "image/jpeg"))],
    ).json()["evidence"][0]
    stored = next((tmp_path / "uploads" / claim["id"]).glob("*"))
    stored.write_bytes(b"<script>alert(1)</script>")
    response = client.get(uploaded["content_url"], headers=headers(client, "adjuster"))
    assert response.status_code == 404


def test_unexpected_error_is_generic_and_logged(client: TestClient, monkeypatch, caplog):
    def fail(_self):
        raise RuntimeError("provider-secret-should-not-leak")

    monkeypatch.setattr(ClaimService, "list_claims", fail)
    response = client.get("/api/claims", headers=headers(client, "admin"))
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "provider-secret-should-not-leak" not in response.text
    assert "provider-secret-should-not-leak" in caplog.text


@pytest.mark.parametrize(
    "method,path,service_method,error_type,body",
    [
        ("POST", "/api/claims/CLM-000001/damage-analysis", "run_damage_analysis", ValueError, None),
        ("POST", "/api/claims/CLM-000001/copilot-conclusions/1/review", "review_copilot_conclusion", RuntimeError, {"status": "APPROVED", "comment": "Reviewed"}),
    ],
)
def test_unexpected_provider_errors_are_not_returned_as_business_errors(
    client: TestClient, monkeypatch, method: str, path: str, service_method: str, error_type: type[Exception], body: dict | None
):
    def fail(*_args, **_kwargs):
        raise error_type("private-provider-detail")

    monkeypatch.setattr(ClaimService, service_method, fail)
    response = client.request(method, path, headers=headers(client, "admin"), json=body)
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "private-provider-detail" not in response.text


def test_nested_resources_cannot_be_accessed_through_another_claim(client: TestClient):
    def create_claim(name: str) -> dict:
        response = client.post("/api/claims", headers=headers(client, "admin"), json={
            "claimant_name": name,
            "vehicle": {"make": "Toyota", "model": "Camry", "year": 2022},
            "incident": {
                "occurred_at": "2026-09-09T08:30:00+07:00",
                "location": "Ho Chi Minh City",
                "description": "Rear impact while stopped.",
            },
        })
        assert response.status_code == 201
        return response.json()

    first = create_claim("Mai Nguyen")
    second = create_claim("Lan Tran")
    files = [
        ("files", (f"{index}.jpg", b"\xff\xd8\xffimage", "image/jpeg"))
        for index in range(5)
    ]
    uploaded = client.post(
        f"/api/claims/{first['id']}/evidence", headers=headers(client, "admin"),
        data={"categories": ["VEHICLE_DAMAGE_IMAGE", "ID_CARD", "INSURANCE_POLICY", "VEHICLE_REGISTRATION", "DRIVER_LICENSE"]},
        files=files,
    )
    assert uploaded.status_code == 200
    evidence_id = uploaded.json()["evidence"][0]["id"]
    assert client.get(
        f"/api/claims/{second['id']}/evidence/{evidence_id}/content",
        headers=headers(client, "adjuster"),
    ).status_code == 404
    assert client.delete(
        f"/api/claims/{second['id']}/evidence/{evidence_id}",
        headers=headers(client, "admin"),
    ).status_code == 404

    started = client.post(
        f"/api/claims/{first['id']}/analysis-runs", headers=headers(client, "adjuster")
    )
    assert started.status_code == 202
    run = client.get(f"/api/claims/{first['id']}", headers=headers(client, "adjuster")).json()["latest_analysis_run"]
    run_id = run["id"]
    extraction = next(result["extraction"] for result in run["document_ocr_results"] if result["extraction"])
    field_id = extraction["fields"][0]["id"]
    assert client.post(
        f"/api/claims/{second['id']}/analysis-runs/{run_id}/ai-review",
        headers=headers(client, "adjuster"),
    ).status_code == 404
    assert client.put(
        f"/api/claims/{second['id']}/analysis-runs/{run_id}/extraction-fields",
        headers=headers(client, "adjuster"), json={"fields": [{"id": field_id, "confirmed_value": "unrelated"}]},
    ).status_code == 404
    assert client.patch(
        f"/api/claims/{second['id']}/analysis-runs/{run_id}/extraction-fields/{field_id}",
        headers=headers(client, "adjuster"), json={"confirmed_value": "unrelated"},
    ).status_code == 404
    document = next(item for item in run["document_analyses"] if item["fields"])
    assert client.patch(
        f"/api/claims/{second['id']}/document-analyses/{document['id']}/fields/{document['fields'][0]['id']}",
        headers=headers(client, "adjuster"), json={"reviewed_value": "unrelated"},
    ).status_code == 404

    damage = client.post(f"/api/claims/{first['id']}/damage-analysis", headers=headers(client, "adjuster"))
    assert damage.status_code == 200
    conclusion_id = damage.json()["copilot_conclusion"]["id"]
    assert client.post(
        f"/api/claims/{second['id']}/copilot-conclusions/{conclusion_id}/review",
        headers=headers(client, "adjuster"),
        json={"status": "APPROVED", "comment": "Cross claim review"},
    ).status_code == 404
    assert client.post(
        f"/api/claims/{second['id']}/copilot-conclusions/{conclusion_id}/review/revert",
        headers=headers(client, "adjuster"), json={"note": "Cross claim revert"},
    ).status_code == 404
