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
    monkeypatch.setenv("LLM_MODE", "mock")
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


def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
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


def test_admin_can_update_persisted_assessment_rules_with_an_audit_record(client: TestClient):
    initial_response = client.get("/api/admin/assessment-rules", headers=admin_headers(client))

    assert initial_response.status_code == 200
    assert initial_response.json()["values"] == {
        "confidence_threshold": 0.7,
        "repair_max_percentage": 40.0,
        "replacement_min_percentage": 60.0,
    }

    update_response = client.put(
        "/api/admin/assessment-rules",
        headers=admin_headers(client),
        json={
            "confidence_threshold": 0.8,
            "repair_max_percentage": 35,
            "replacement_min_percentage": 70,
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["values"]["confidence_threshold"] == 0.8
    assert update_response.json()["updated_by"] == "admin@example.com"
    history_response = client.get("/api/admin/assessment-rules/history", headers=admin_headers(client))
    assert history_response.status_code == 200
    assert history_response.json()[0]["changed_by"] == "admin@example.com"
    assert history_response.json()[0]["old_values"]["repair_max_percentage"] == 40.0
    assert history_response.json()[0]["new_values"]["replacement_min_percentage"] == 70.0


def test_adjuster_cannot_update_assessment_rules(client: TestClient):
    response = client.put(
        "/api/admin/assessment-rules",
        headers=adjuster_headers(client),
        json={
            "confidence_threshold": 0.8,
            "repair_max_percentage": 35,
            "replacement_min_percentage": 70,
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin access required"}


def test_invalid_assessment_rule_combinations_are_rejected(client: TestClient):
    response = client.put(
        "/api/admin/assessment-rules",
        headers=admin_headers(client),
        json={
            "confidence_threshold": 0.8,
            "repair_max_percentage": 70,
            "replacement_min_percentage": 60,
        },
    )

    assert response.status_code == 422
    assert "repair_max_percentage must be less than replacement_min_percentage" in response.text


def test_damage_analyses_preserve_the_active_rules_used_at_runtime(client: TestClient):
    update_response = client.put(
        "/api/admin/assessment-rules",
        headers=admin_headers(client),
        json={
            "confidence_threshold": 0.8,
            "repair_max_percentage": 20,
            "replacement_min_percentage": 60,
        },
    )
    assert update_response.status_code == 200

    first_claim = create_claim(client)
    upload_damage_images(client, first_claim["id"], ["repair.jpg"])
    first_analysis = client.post(
        f"/api/claims/{first_claim['id']}/damage-analysis", headers=adjuster_headers(client)
    ).json()
    assert first_analysis["assessment"] == "MANUAL_INSPECTION_REQUIRED"
    assert first_analysis["rules"]["repair_max_percentage"] == 20.0

    update_response = client.put(
        "/api/admin/assessment-rules",
        headers=admin_headers(client),
        json={
            "confidence_threshold": 0.8,
            "repair_max_percentage": 40,
            "replacement_min_percentage": 60,
        },
    )
    assert update_response.status_code == 200

    second_claim = create_claim(client)
    upload_damage_images(client, second_claim["id"], ["repair.jpg"])
    second_analysis = client.post(
        f"/api/claims/{second_claim['id']}/damage-analysis", headers=adjuster_headers(client)
    ).json()
    assert second_analysis["assessment"] == "REPAIR_LIKELY"
    assert second_analysis["rules"]["repair_max_percentage"] == 40.0

    first_detail = client.get(f"/api/claims/{first_claim['id']}", headers=adjuster_headers(client)).json()
    assert first_detail["latest_damage_analysis"]["rules"]["repair_max_percentage"] == 20.0


def test_replacement_analysis_returns_a_reference_oem_part_price(client: TestClient):
    claim = create_claim(client)
    upload_damage_images(client, claim["id"], ["replacement.jpg"])

    response = client.post(f"/api/claims/{claim['id']}/damage-analysis", headers=adjuster_headers(client))

    assert response.status_code == 200
    analysis = response.json()
    assert analysis["reference_price_status"] == "FOUND"
    assert analysis["reference_prices"] == [{
        "part_identity": "front_left_door",
        "amount": 950.0,
        "currency": "USD",
        "source_name": "Mock OEM Parts Catalog",
        "source_url": "https://example.com/oem-parts/front-left-door",
        "price_type": "REFERENCE_OEM_PART_PRICE",
        "retrieved_at": analysis["reference_prices"][0]["retrieved_at"],
        "status": "FOUND",
        "failure_reason": None,
    }]


def test_non_replacement_analysis_skips_reference_price_lookup(client: TestClient):
    claim = create_claim(client)
    upload_damage_images(client, claim["id"], ["repair.jpg"])

    response = client.post(f"/api/claims/{claim['id']}/damage-analysis", headers=adjuster_headers(client))

    assert response.status_code == 200
    assert response.json()["reference_price_status"] == "NOT_REQUESTED"
    assert response.json()["reference_prices"] == []


def test_non_replacement_analysis_can_explicitly_request_reference_price_lookup(client: TestClient):
    claim = create_claim(client)
    upload_damage_images(client, claim["id"], ["repair.jpg"])

    response = client.post(
        f"/api/claims/{claim['id']}/damage-analysis?force_reference_price_lookup=true",
        headers=adjuster_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["reference_price_status"] == "FOUND"
    assert response.json()["reference_prices"][0]["part_identity"] == "rear_bumper"


def test_reference_price_lookup_failure_does_not_fail_replacement_analysis(client: TestClient, monkeypatch):
    monkeypatch.setenv("PART_SEARCH_MODE", "unavailable")
    get_settings.cache_clear()
    claim = create_claim(client)
    upload_damage_images(client, claim["id"], ["replacement.jpg"])

    response = client.post(f"/api/claims/{claim['id']}/damage-analysis", headers=adjuster_headers(client))

    assert response.status_code == 200
    analysis = response.json()
    assert analysis["assessment"] == "REPLACEMENT_LIKELY"
    assert analysis["reference_price_status"] == "UNAVAILABLE"
    assert analysis["reference_prices"][0]["status"] == "UNAVAILABLE"
    assert "unavailable" in analysis["reference_prices"][0]["failure_reason"].lower()


def test_mock_llm_copilot_returns_a_deterministic_fallback_conclusion(client: TestClient):
    claim = create_claim(client)
    upload_damage_images(client, claim["id"], ["replacement.jpg"])

    response = client.post(f"/api/claims/{claim['id']}/damage-analysis", headers=adjuster_headers(client))

    assert response.status_code == 200
    conclusion = response.json()["copilot_conclusion"]
    assert conclusion["status"] == "FALLBACK"
    assert conclusion["recommendation"] == "MANUAL_ADJUSTER_REVIEW"
    assert conclusion["findings"][0]["vehicle_part"] == "front_left_door"
    assert conclusion["reference_prices"][0]["amount"] == 950.0
    assert conclusion["summary"]


def test_missing_llm_credentials_returns_unavailable_conclusion_without_hiding_analysis(client: TestClient, monkeypatch):
    monkeypatch.setenv("LLM_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    claim = create_claim(client)
    upload_damage_images(client, claim["id"], ["repair.jpg"])

    response = client.post(f"/api/claims/{claim['id']}/damage-analysis", headers=adjuster_headers(client))

    assert response.status_code == 200
    analysis = response.json()
    assert analysis["assessment"] == "REPAIR_LIKELY"
    assert analysis["copilot_conclusion"]["status"] == "LLM_UNAVAILABLE"
    assert analysis["copilot_conclusion"]["fallback_summary"]


def create_reviewable_conclusion(client: TestClient) -> tuple[dict[str, object], dict[str, object]]:
    claim = create_claim(client)
    upload_damage_images(client, claim["id"], ["repair.jpg"])
    analysis = client.post(
        f"/api/claims/{claim['id']}/damage-analysis", headers=adjuster_headers(client)
    ).json()
    return claim, analysis["copilot_conclusion"]


def test_adjuster_can_approve_an_ai_conclusion_and_view_persisted_review_history(client: TestClient):
    claim, conclusion = create_reviewable_conclusion(client)

    response = client.post(
        f"/api/claims/{claim['id']}/copilot-conclusions/{conclusion['id']}/review",
        headers=adjuster_headers(client),
        json={"status": "APPROVED"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "AI_APPROVED"
    assert response.json()["latest_damage_analysis"]["copilot_conclusion"]["review_history"] == [{
        "claim_id": claim["id"],
        "conclusion_id": conclusion["id"],
        "status": "APPROVED",
        "reason_category": None,
        "comment": None,
        "reviewer": "adjuster@example.com",
        "reviewed_at": response.json()["latest_damage_analysis"]["copilot_conclusion"]["review_history"][0]["reviewed_at"],
    }]
    assert response.json()["copilot_review_history"][0]["conclusion_id"] == conclusion["id"]


def test_rejecting_an_ai_conclusion_requires_a_category_and_comment_at_the_api(client: TestClient):
    claim, conclusion = create_reviewable_conclusion(client)

    missing_reason = client.post(
        f"/api/claims/{claim['id']}/copilot-conclusions/{conclusion['id']}/review",
        headers=adjuster_headers(client),
        json={"status": "REJECTED"},
    )
    assert missing_reason.status_code == 422

    response = client.post(
        f"/api/claims/{claim['id']}/copilot-conclusions/{conclusion['id']}/review",
        headers=adjuster_headers(client),
        json={
            "status": "REJECTED",
            "reason_category": "DAMAGE_ASSESSMENT_ISSUE",
            "comment": "The rear bumper damage area is understated in the annotated image.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "AI_REJECTED"
    review = response.json()["latest_damage_analysis"]["copilot_conclusion"]["review_history"][0]
    assert review["reason_category"] == "DAMAGE_ASSESSMENT_ISSUE"
    assert review["comment"] == "The rear bumper damage area is understated in the annotated image."


def test_admin_cannot_review_an_ai_conclusion_and_a_conclusion_cannot_be_reviewed_twice(client: TestClient):
    claim, conclusion = create_reviewable_conclusion(client)

    admin_response = client.post(
        f"/api/claims/{claim['id']}/copilot-conclusions/{conclusion['id']}/review",
        headers=admin_headers(client),
        json={"status": "APPROVED"},
    )
    assert admin_response.status_code == 403

    approved = client.post(
        f"/api/claims/{claim['id']}/copilot-conclusions/{conclusion['id']}/review",
        headers=adjuster_headers(client),
        json={"status": "APPROVED"},
    )
    assert approved.status_code == 200

    duplicate = client.post(
        f"/api/claims/{claim['id']}/copilot-conclusions/{conclusion['id']}/review",
        headers=adjuster_headers(client),
        json={"status": "APPROVED"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "AI conclusion has already been reviewed"}
