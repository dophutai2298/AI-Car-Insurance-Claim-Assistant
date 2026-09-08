from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.services.evidence_storage import LocalEvidenceStorage


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
    monkeypatch.setenv("UPLOAD_ROOT", str(tmp_path / "uploads"))
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


def test_adjuster_can_upload_multiple_evidence_files_and_open_image_content(client: TestClient, tmp_path):
    claim = create_claim(client)

    response = client.post(
        f"/api/claims/{claim['id']}/evidence",
        headers=adjuster_headers(client),
        data={"categories": ["VEHICLE_DAMAGE_IMAGE", "INSURANCE_POLICY"]},
        files=[
            ("files", ("front-damage.jpg", b"damage-image-content", "image/jpeg")),
            ("files", ("policy.pdf", b"policy-document-content", "application/pdf")),
        ],
    )

    assert response.status_code == 200
    evidence = response.json()["evidence"]
    assert sorted((item["category"], item["original_filename"]) for item in evidence) == [
        ("INSURANCE_POLICY", "policy.pdf"),
        ("VEHICLE_DAMAGE_IMAGE", "front-damage.jpg"),
    ]
    assert {item["file_size"] for item in evidence} == {20, 23}
    assert (tmp_path / "uploads" / claim["id"]).is_dir()

    image = next(item for item in evidence if item["category"] == "VEHICLE_DAMAGE_IMAGE")
    content = client.get(image["content_url"], headers=adjuster_headers(client))

    assert content.status_code == 200
    assert content.headers["content-type"] == "image/jpeg"
    assert content.content == b"damage-image-content"


def test_evidence_category_mismatch_returns_clear_error_without_metadata_or_files(client: TestClient, tmp_path):
    claim = create_claim(client)

    response = client.post(
        f"/api/claims/{claim['id']}/evidence",
        headers=adjuster_headers(client),
        data={"categories": ["VEHICLE_DAMAGE_IMAGE", "ID_CARD"]},
        files=[("files", ("front-damage.jpg", b"damage-image-content", "image/jpeg"))],
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Each uploaded file must have exactly one evidence category"}
    assert client.get(f"/api/claims/{claim['id']}", headers=adjuster_headers(client)).json()["evidence"] == []
    assert not (tmp_path / "uploads" / claim["id"]).exists()


def test_storage_failure_cleans_up_previously_written_files_and_metadata(client: TestClient, tmp_path, monkeypatch):
    claim = create_claim(client)
    original_write_upload = LocalEvidenceStorage._write_upload

    def fail_for_second_file(self, upload, destination):
        if upload.filename == "policy.pdf":
            raise RuntimeError("stream read failed")
        return original_write_upload(self, upload, destination)

    monkeypatch.setattr(LocalEvidenceStorage, "_write_upload", fail_for_second_file)

    response = client.post(
        f"/api/claims/{claim['id']}/evidence",
        headers=adjuster_headers(client),
        data={"categories": ["VEHICLE_DAMAGE_IMAGE", "INSURANCE_POLICY"]},
        files=[
            ("files", ("front-damage.jpg", b"damage-image-content", "image/jpeg")),
            ("files", ("policy.pdf", b"policy-document-content", "application/pdf")),
        ],
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to store uploaded evidence"}
    assert client.get(f"/api/claims/{claim['id']}", headers=adjuster_headers(client)).json()["evidence"] == []
    assert list((tmp_path / "uploads" / claim["id"]).glob("*")) == []


def upload_damage_images(client: TestClient, claim_id: str, filenames: list[str]) -> None:
    response = client.post(
        f"/api/claims/{claim_id}/evidence",
        headers=adjuster_headers(client),
        data={"categories": ["VEHICLE_DAMAGE_IMAGE"] * len(filenames)},
        files=[("files", (filename, b"damage-image-content", "image/jpeg")) for filename in filenames],
    )
    assert response.status_code == 200


def test_damage_analysis_returns_normalized_repair_fixture_and_persists_it(client: TestClient):
    claim = create_claim(client)
    upload_damage_images(client, claim["id"], ["repair.jpg"])

    response = client.post(f"/api/claims/{claim['id']}/damage-analysis", headers=adjuster_headers(client))

    assert response.status_code == 200
    analysis = response.json()
    assert analysis["assessment"] == "REPAIR_LIKELY"
    assert analysis["detections"] == [{
        "vehicle_part": "rear_bumper",
        "damage_type": "dent",
        "damage_percentage": 32.5,
        "confidence": 0.91,
        "status": "DETECTED",
        "annotated_evidence": {
            "id": 1,
            "category": "VEHICLE_DAMAGE_IMAGE",
            "original_filename": "repair.jpg",
            "content_type": "image/jpeg",
            "file_size": 20,
            "uploaded_at": analysis["detections"][0]["annotated_evidence"]["uploaded_at"],
            "content_url": "/api/claims/CLM-000001/evidence/1/content",
        },
    }]
    detail = client.get(f"/api/claims/{claim['id']}", headers=adjuster_headers(client)).json()
    assert detail["status"] == "REVIEW_REQUIRED"
    assert detail["latest_damage_analysis"]["id"] == analysis["id"]


@pytest.mark.parametrize(
    ("filename", "assessment", "warning"),
    [
        ("replacement.jpg", "REPLACEMENT_LIKELY", None),
        ("low-confidence.jpg", "MANUAL_INSPECTION_REQUIRED", "confidence threshold"),
        ("no-damage.jpg", "NO_DAMAGE", "does not guarantee"),
    ],
)
def test_damage_analysis_returns_stable_fixture_assessments(client: TestClient, filename, assessment, warning):
    claim = create_claim(client)
    upload_damage_images(client, claim["id"], [filename])

    response = client.post(f"/api/claims/{claim['id']}/damage-analysis", headers=adjuster_headers(client))

    assert response.status_code == 200
    assert response.json()["assessment"] == assessment
    if warning is None:
        assert response.json()["warning"] is None
    else:
        assert warning in response.json()["warning"]


def test_damage_analysis_supports_multiple_images_and_detections(client: TestClient):
    claim = create_claim(client)
    upload_damage_images(client, claim["id"], ["multiple.jpg", "repair.jpg"])

    response = client.post(f"/api/claims/{claim['id']}/damage-analysis", headers=adjuster_headers(client))

    assert response.status_code == 200
    assert len(response.json()["detections"]) == 3


def test_damage_analysis_requires_vehicle_damage_images(client: TestClient):
    claim = create_claim(client)

    response = client.post(f"/api/claims/{claim['id']}/damage-analysis", headers=adjuster_headers(client))

    assert response.status_code == 422
    assert response.json() == {"detail": "Upload at least one vehicle damage image before running analysis"}
