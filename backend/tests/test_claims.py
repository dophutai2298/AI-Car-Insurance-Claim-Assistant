from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.api.routes import claims as claim_routes
from app.services.document_ocr import DocumentOcrError, DocumentOcrResult
from app.services.document_extraction import (
    DeterministicDocumentExtractionAdapter,
    IdentityCardExtraction,
)
from app.services.evidence_storage import LocalEvidenceStorage
from app.services.llm_copilot import LlmCopilotService


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
    monkeypatch.setenv("DOCUMENT_OCR_MODE", "mock")
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


def test_adjuster_can_persist_and_edit_claim_incident_information(client: TestClient):
    claim = create_claim(client)

    response = client.patch(
        f"/api/claims/{claim['id']}/information",
        headers=adjuster_headers(client),
        json={
            "claimant_name": "Mai Nguyen",
            "vehicle": claim["vehicle"],
            "incident": {
                "occurred_at": "2026-09-09T08:30:00+07:00",
                "location": "Nguyen Huu Canh Street, Ho Chi Minh City",
                "description": "Rear impact while the vehicle was stopped at a traffic light.",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["incident"] == {
        "occurred_at": "2026-09-09T01:30:00Z",
        "location": "Nguyen Huu Canh Street, Ho Chi Minh City",
        "description": "Rear impact while the vehicle was stopped at a traffic light.",
    }
    persisted = client.get(
        f"/api/claims/{claim['id']}", headers=adjuster_headers(client)
    ).json()
    assert persisted["incident"] == response.json()["incident"]


def test_vehicle_manufacturer_catalog_is_seeded_and_admin_can_manage_active_status(client: TestClient):
    catalog_response = client.get("/api/vehicle-makes", headers=adjuster_headers(client))

    assert catalog_response.status_code == 200
    assert {item["name"] for item in catalog_response.json()} >= {"Toyota", "Honda", "VinFast"}
    assert all(item["is_active"] for item in catalog_response.json())

    blank_name_response = client.post(
        "/api/admin/vehicle-makes",
        headers=admin_headers(client),
        json={"name": "   "},
    )
    assert blank_name_response.status_code == 422

    create_response = client.post(
        "/api/admin/vehicle-makes",
        headers=admin_headers(client),
        json={"name": "BYD"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created == {"id": created["id"], "name": "BYD", "is_active": True}

    disable_response = client.put(
        f"/api/admin/vehicle-makes/{created['id']}",
        headers=admin_headers(client),
        json={"name": "BYD Auto", "is_active": False},
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["name"] == "BYD Auto"
    assert disable_response.json()["is_active"] is False

    admin_catalog = client.get("/api/admin/vehicle-makes", headers=admin_headers(client))
    assert any(item["name"] == "BYD Auto" and not item["is_active"] for item in admin_catalog.json())

    reenable_response = client.put(
        f"/api/admin/vehicle-makes/{created['id']}",
        headers=admin_headers(client),
        json={"name": "BYD Auto", "is_active": True},
    )
    assert reenable_response.status_code == 200
    assert reenable_response.json()["is_active"] is True


def test_claim_creation_rejects_a_disabled_vehicle_manufacturer(client: TestClient):
    vehicle_makes = client.get("/api/admin/vehicle-makes", headers=admin_headers(client)).json()
    toyota = next(item for item in vehicle_makes if item["name"] == "Toyota")
    disable_response = client.put(
        f"/api/admin/vehicle-makes/{toyota['id']}",
        headers=admin_headers(client),
        json={"name": "Toyota", "is_active": False},
    )
    assert disable_response.status_code == 200

    response = client.post(
        "/api/claims",
        headers=adjuster_headers(client),
        json={
            "claimant_name": "Mai Nguyen",
            "vehicle": {"make": "Toyota", "model": "Camry", "year": 2022},
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Vehicle manufacturer is unavailable for new claims"}


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


def test_other_document_groups_keep_their_label_and_evidence_can_be_removed(client: TestClient, tmp_path):
    claim = create_claim(client)

    upload = client.post(
        f"/api/claims/{claim['id']}/evidence",
        headers=adjuster_headers(client),
        data={
            "categories": ["OTHER_DOCUMENT", "OTHER_DOCUMENT"],
            "other_document_label": "Police Accident Report",
        },
        files=[
            ("files", ("report-1.jpg", b"report-one", "image/jpeg")),
            ("files", ("report-2.jpg", b"report-two", "image/jpeg")),
        ],
    )

    assert upload.status_code == 200
    evidence = upload.json()["evidence"]
    assert {item["group_label"] for item in evidence} == {"Police Accident Report"}
    assert len({item["group_id"] for item in evidence}) == 1

    removed = client.delete(
        f"/api/claims/{claim['id']}/evidence/{evidence[0]['id']}",
        headers=adjuster_headers(client),
    )

    assert removed.status_code == 200
    assert [item["id"] for item in removed.json()["evidence"]] == [evidence[1]["id"]]
    assert len(list((tmp_path / "uploads" / claim["id"]).glob("*"))) == 1


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


def prepare_claim_for_workflow_analysis(
    client: TestClient,
    *,
    driver_license_filename: str = "driver-license.jpg",
) -> dict[str, object]:
    claim = create_claim(client)
    information = client.patch(
        f"/api/claims/{claim['id']}/information",
        headers=adjuster_headers(client),
        json={
            "claimant_name": claim["claimant_name"],
            "vehicle": claim["vehicle"],
            "incident": {
                "occurred_at": "2026-09-09T08:30:00+07:00",
                "location": "District 1, Ho Chi Minh City",
                "description": "Rear impact while stopped at a traffic light.",
            },
        },
    )
    assert information.status_code == 200
    upload = client.post(
        f"/api/claims/{claim['id']}/evidence",
        headers=adjuster_headers(client),
        data={
            "categories": [
                "VEHICLE_DAMAGE_IMAGE",
                "ID_CARD",
                "INSURANCE_POLICY",
                "VEHICLE_REGISTRATION",
                "DRIVER_LICENSE",
            ]
        },
        files=[
            ("files", ("repair.jpg", b"damage", "image/jpeg")),
            ("files", ("id-card.jpg", b"id-card", "image/jpeg")),
            ("files", ("policy.pdf", b"policy", "application/pdf")),
            ("files", ("registration.jpg", b"registration", "image/jpeg")),
            ("files", (driver_license_filename, b"license", "image/jpeg")),
        ],
    )
    assert upload.status_code == 200
    return claim


def test_workflow_analysis_returns_pending_then_persists_grouped_results(client: TestClient):
    claim = prepare_claim_for_workflow_analysis(client)

    started = client.post(
        f"/api/claims/{claim['id']}/analysis-runs",
        headers=adjuster_headers(client),
    )

    assert started.status_code == 202
    assert started.json()["status"] == "PENDING"
    detail = client.get(f"/api/claims/{claim['id']}", headers=adjuster_headers(client)).json()
    run = detail["latest_analysis_run"]
    assert run["status"] == "PARTIAL"
    assert run["damage_status"] == "COMPLETED"
    assert run["damage_analysis"]["assessment"] == "REPAIR_LIKELY"
    assert {item["document_type"] for item in run["document_analyses"]} == {
        "ID_CARD",
        "INSURANCE_POLICY",
        "VEHICLE_REGISTRATION",
        "DRIVER_LICENSE",
    }
    registration = next(
        item for item in run["document_analyses"] if item["document_type"] == "VEHICLE_REGISTRATION"
    )
    assert registration["status"] == "COMPLETED"
    assert {field["key"] for field in registration["fields"]} >= {"owner_name", "license_plate"}
    assert all(field["original_ai_value"] == field["reviewed_value"] for field in registration["fields"])
    policy = next(
        item for item in run["document_ocr_results"] if item["document_type"] == "INSURANCE_POLICY"
    )
    assert policy["status"] == "FAILED"


def test_workflow_analysis_persists_ocr_results_per_image_and_marks_unsupported_files(client: TestClient):
    claim = prepare_claim_for_workflow_analysis(client)
    second_id_card = client.post(
        f"/api/claims/{claim['id']}/evidence",
        headers=adjuster_headers(client),
        data={"categories": ["ID_CARD"]},
        files=[("files", ("id-card-back.png", b"id-card-back", "image/png"))],
    )
    assert second_id_card.status_code == 200

    started = client.post(
        f"/api/claims/{claim['id']}/analysis-runs",
        headers=adjuster_headers(client),
    )
    assert started.status_code == 202

    run = client.get(f"/api/claims/{claim['id']}", headers=adjuster_headers(client)).json()[
        "latest_analysis_run"
    ]
    ocr_results = run["document_ocr_results"]
    id_card_results = [item for item in ocr_results if item["document_type"] == "ID_CARD"]
    policy_result = next(item for item in ocr_results if item["document_type"] == "INSURANCE_POLICY")

    assert len(id_card_results) == 2
    assert all(item["status"] == "COMPLETED" and item["raw_text"] for item in id_card_results)
    assert policy_result["status"] == "FAILED"
    assert "supported image" in policy_result["warning"].lower()
    assert run["status"] == "PARTIAL"


def test_identity_and_policy_extraction_persists_structured_fields_and_confirmed_edits(
    client: TestClient,
):
    claim = prepare_claim_for_workflow_analysis(client)
    policy_image = client.post(
        f"/api/claims/{claim['id']}/evidence",
        headers=adjuster_headers(client),
        data={"categories": ["INSURANCE_POLICY"]},
        files=[("files", ("policy-card.jpg", b"policy-card", "image/jpeg"))],
    )
    assert policy_image.status_code == 200

    started = client.post(
        f"/api/claims/{claim['id']}/analysis-runs",
        headers=adjuster_headers(client),
    )
    assert started.status_code == 202

    detail = client.get(
        f"/api/claims/{claim['id']}", headers=adjuster_headers(client)
    ).json()
    run = detail["latest_analysis_run"]
    id_card = next(
        item
        for item in run["document_ocr_results"]
        if item["original_filename"] == "id-card.jpg"
    )
    policy = next(
        item
        for item in run["document_ocr_results"]
        if item["original_filename"] == "policy-card.jpg"
    )

    assert id_card["raw_text"]
    assert id_card["extraction"]["status"] == "COMPLETED"
    assert id_card["extraction"]["prompt_version"] == "document-extraction-v1"
    identity_fields = {
        field["field_key"]: field for field in id_card["extraction"]["fields"]
    }
    assert set(identity_fields) == {
        "full_name",
        "identity_number",
        "date_of_birth",
        "place_of_origin",
        "expiry_date",
    }
    assert identity_fields["identity_number"]["ai_extracted_value"] == "079203001234"
    assert identity_fields["identity_number"]["confirmed_value"] == "079203001234"
    assert "confidence" not in identity_fields["identity_number"]

    policy_fields = {
        field["field_key"]: field for field in policy["extraction"]["fields"]
    }
    assert set(policy_fields) == {"vehicle_owner", "vehicle_brand"}
    assert policy_fields["vehicle_owner"]["ai_extracted_value"] == "Nguyen Van A"
    assert policy_fields["vehicle_brand"]["ai_extracted_value"] == "Toyota"

    raw_ocr_before_edit = id_card["raw_text"]
    full_name = identity_fields["full_name"]
    corrected = client.patch(
        f"/api/claims/{claim['id']}/analysis-runs/{run['id']}/extraction-fields/{full_name['id']}",
        headers=adjuster_headers(client),
        json={"confirmed_value": "Mai Nguyen"},
    )
    assert corrected.status_code == 200

    refreshed = client.get(
        f"/api/claims/{claim['id']}", headers=adjuster_headers(client)
    ).json()["latest_analysis_run"]
    refreshed_id_card = next(
        item
        for item in refreshed["document_ocr_results"]
        if item["original_filename"] == "id-card.jpg"
    )
    refreshed_name = next(
        field
        for field in refreshed_id_card["extraction"]["fields"]
        if field["field_key"] == "full_name"
    )
    assert refreshed_id_card["raw_text"] == raw_ocr_before_edit
    assert refreshed_name["ai_extracted_value"] == "Nguyen Van A"
    assert refreshed_name["confirmed_value"] == "Mai Nguyen"

    reviewed = client.post(
        f"/api/claims/{claim['id']}/analysis-runs/{run['id']}/ai-review",
        headers=adjuster_headers(client),
    )
    assert reviewed.status_code == 200
    locked_edit = client.patch(
        f"/api/claims/{claim['id']}/analysis-runs/{run['id']}/extraction-fields/{full_name['id']}",
        headers=adjuster_headers(client),
        json={"confirmed_value": "Another Name"},
    )
    assert locked_edit.status_code == 409


def test_registration_and_driver_license_extraction_supports_multiple_images_and_null_fields(
    client: TestClient,
):
    claim = prepare_claim_for_workflow_analysis(client)
    second_registration = client.post(
        f"/api/claims/{claim['id']}/evidence",
        headers=adjuster_headers(client),
        data={"categories": ["VEHICLE_REGISTRATION"]},
        files=[("files", ("registration-back.jpg", b"registration-back", "image/jpeg"))],
    )
    assert second_registration.status_code == 200

    started = client.post(
        f"/api/claims/{claim['id']}/analysis-runs",
        headers=adjuster_headers(client),
    )
    assert started.status_code == 202

    run = client.get(
        f"/api/claims/{claim['id']}", headers=adjuster_headers(client)
    ).json()["latest_analysis_run"]
    registrations = [
        result
        for result in run["document_ocr_results"]
        if result["document_type"] == "VEHICLE_REGISTRATION"
    ]
    driver_license = next(
        result
        for result in run["document_ocr_results"]
        if result["document_type"] == "DRIVER_LICENSE"
    )

    assert len(registrations) == 2
    for registration in registrations:
        extraction = registration["extraction"]
        fields = {field["field_key"]: field for field in extraction["fields"]}
        assert extraction["source_evidence_id"] == registration["source_evidence_id"]
        assert extraction["document_type"] == "VEHICLE_REGISTRATION"
        assert set(fields) == {
            "vehicle_owner",
            "vehicle_brand",
            "vehicle_type",
            "license_plate",
        }
        assert fields["vehicle_owner"]["ai_extracted_value"] == "Nguyen Van A"
        assert fields["vehicle_brand"]["ai_extracted_value"] == "Toyota"
        assert fields["vehicle_type"]["ai_extracted_value"] == "Ô tô con"
        assert fields["license_plate"]["ai_extracted_value"] == "51H-123.45"
        assert all(field["source_evidence_id"] == registration["source_evidence_id"] for field in fields.values())
        assert all("confidence" not in field for field in fields.values())
        assert registration["field_validations"] == []

    driver_fields = {
        field["field_key"]: field
        for field in driver_license["extraction"]["fields"]
    }
    assert set(driver_fields) == {"license_number", "full_name", "expiry_date"}
    assert driver_fields["license_number"]["ai_extracted_value"] == "079012345678"
    assert driver_fields["full_name"]["ai_extracted_value"] is None
    assert driver_fields["expiry_date"]["ai_extracted_value"] is None
    assert driver_license["field_validations"] == []


def test_document_extraction_selects_category_prompt_and_isolates_malformed_output(
    client: TestClient, monkeypatch
):
    class CapturingExtractionAdapter:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []
            self.delegate = DeterministicDocumentExtractionAdapter()

        def extract(self, definition, raw_ocr_text):
            self.calls.append((definition.category.value, definition.system_prompt))
            if definition.category.value == "INSURANCE_POLICY":
                return {"unexpected": "malformed"}
            if definition.category.value == "ID_CARD":
                return IdentityCardExtraction(
                    full_name="Nguyen Van A",
                    identity_number="000123456789",
                    date_of_birth=None,
                    place_of_origin=None,
                    expiry_date=None,
                )
            return self.delegate.extract(definition, raw_ocr_text)

    adapter = CapturingExtractionAdapter()
    monkeypatch.setattr(
        claim_routes, "get_document_extraction_adapter", lambda settings: adapter
    )
    claim = prepare_claim_for_workflow_analysis(client)
    uploaded = client.post(
        f"/api/claims/{claim['id']}/evidence",
        headers=adjuster_headers(client),
        data={"categories": ["INSURANCE_POLICY"]},
        files=[("files", ("policy-card.jpg", b"policy-card", "image/jpeg"))],
    )
    assert uploaded.status_code == 200

    client.post(
        f"/api/claims/{claim['id']}/analysis-runs",
        headers=adjuster_headers(client),
    )
    run = client.get(
        f"/api/claims/{claim['id']}", headers=adjuster_headers(client)
    ).json()["latest_analysis_run"]

    id_call = next(item for item in adapter.calls if item[0] == "ID_CARD")
    policy_call = next(item for item in adapter.calls if item[0] == "INSURANCE_POLICY")
    assert "Citizen Identity Card" in id_call[1]
    assert "`full_name`" in id_call[1]
    assert "Insurance Policy" in policy_call[1]

    id_card = next(
        item
        for item in run["document_ocr_results"]
        if item["original_filename"] == "id-card.jpg"
    )
    policy = next(
        item
        for item in run["document_ocr_results"]
        if item["original_filename"] == "policy-card.jpg"
    )
    identity_number = next(
        field
        for field in id_card["extraction"]["fields"]
        if field["field_key"] == "identity_number"
    )
    assert identity_number["ai_extracted_value"] == "000123456789"
    assert next(
        field
        for field in id_card["extraction"]["fields"]
        if field["field_key"] == "date_of_birth"
    )["ai_extracted_value"] is None
    assert policy["raw_text"]
    assert policy["extraction"]["status"] == "FAILED"
    assert policy["extraction"]["fields"] == []
    assert "ValidationError" in policy["extraction"]["warning"]
    assert all(
        item["extraction"]["status"] == "COMPLETED"
        for item in run["document_ocr_results"]
        if item["status"] == "COMPLETED" and item["document_type"] != "INSURANCE_POLICY"
    )


def test_workflow_analysis_uses_injected_ocr_adapter_once_per_supported_document_image(
    client: TestClient, monkeypatch
):
    class FakeOcrAdapter:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def extract(self, evidence, source_path):
            self.calls.append(evidence.id)
            if evidence.original_filename == "registration.jpg":
                raise DocumentOcrError("OCR fixture failure")
            return DocumentOcrResult(
                raw_text=f"OCR text for {evidence.original_filename}",
                adapter_name="fake-ocr",
                metadata={"fixture": True},
            )

    adapter = FakeOcrAdapter()
    monkeypatch.setattr(claim_routes, "get_document_ocr_adapter", lambda mode: adapter)
    claim = prepare_claim_for_workflow_analysis(client)

    client.post(f"/api/claims/{claim['id']}/analysis-runs", headers=adjuster_headers(client))

    run = client.get(f"/api/claims/{claim['id']}", headers=adjuster_headers(client)).json()[
        "latest_analysis_run"
    ]
    ocr_results = run["document_ocr_results"]
    assert len(adapter.calls) == 3
    assert len(adapter.calls) == len(set(adapter.calls))
    registration = next(item for item in ocr_results if item["original_filename"] == "registration.jpg")
    id_card = next(item for item in ocr_results if item["original_filename"] == "id-card.jpg")
    assert registration["status"] == "FAILED"
    assert registration["warning"] == "OCR fixture failure"
    assert id_card["raw_text"] == "OCR text for id-card.jpg"
    assert id_card["adapter_metadata"] == {"fixture": True}


def test_shared_extraction_replaces_legacy_field_validation_without_blocking_ai_review(
    client: TestClient, monkeypatch
):
    class UnexpectedLegacyFieldAdapter:
        def validate(self, definition, raw_ocr_text, claim_context):
            raise AssertionError("Legacy field validation must not run for extracted documents")

    monkeypatch.setattr(
        claim_routes,
        "get_document_field_validation_adapter",
        lambda settings: UnexpectedLegacyFieldAdapter(),
    )
    claim = prepare_claim_for_workflow_analysis(client)
    client.post(f"/api/claims/{claim['id']}/analysis-runs", headers=adjuster_headers(client))

    detail = client.get(f"/api/claims/{claim['id']}", headers=adjuster_headers(client)).json()
    run = detail["latest_analysis_run"]
    registration_ocr = next(
        item
        for item in run["document_ocr_results"]
        if item["document_type"] == "VEHICLE_REGISTRATION"
    )
    registration_fields = {
        item["field_key"]: item for item in registration_ocr["extraction"]["fields"]
    }
    assert registration_ocr["field_validations"] == []
    assert run["consistency_checks"] == []
    assert registration_fields["vehicle_brand"]["ai_extracted_value"] == "Toyota"
    assert registration_fields["license_plate"]["ai_extracted_value"] == "51H-123.45"

    captured_context: dict[str, object] = {}
    original_generate = LlmCopilotService.generate

    def capture_input(self, input_data):
        captured_context.update(input_data.model_context())
        return original_generate(self, input_data)

    monkeypatch.setattr(LlmCopilotService, "generate", capture_input)
    reviewed = client.post(
        f"/api/claims/{claim['id']}/analysis-runs/{run['id']}/ai-review",
        headers=adjuster_headers(client),
    )

    assert reviewed.status_code == 200
    registration_context = next(
        item
        for item in captured_context["document_analysis"]
        if item["document_type"] == "VEHICLE_REGISTRATION"
    )
    assert registration_context["field_validations"] == []
    assert registration_context["fields"]


def test_adjuster_can_confirm_registration_field_without_changing_ai_or_ocr_values(
    client: TestClient,
):
    claim = prepare_claim_for_workflow_analysis(client)
    client.post(
        f"/api/claims/{claim['id']}/analysis-runs",
        headers=adjuster_headers(client),
    )
    detail = client.get(
        f"/api/claims/{claim['id']}", headers=adjuster_headers(client)
    ).json()
    run = detail["latest_analysis_run"]
    registration = next(
        item
        for item in run["document_ocr_results"]
        if item["document_type"] == "VEHICLE_REGISTRATION"
    )
    plate = next(
        item
        for item in registration["extraction"]["fields"]
        if item["field_key"] == "license_plate"
    )
    raw_ocr = registration["raw_text"]

    corrected = client.patch(
        f"/api/claims/{claim['id']}/analysis-runs/{run['id']}/extraction-fields/{plate['id']}",
        headers=adjuster_headers(client),
        json={"confirmed_value": "51H-999.99"},
    )

    assert corrected.status_code == 200
    corrected_plate = next(
        field
        for result in corrected.json()["latest_analysis_run"]["document_ocr_results"]
        if result["id"] == registration["id"]
        for field in result["extraction"]["fields"]
        if field["id"] == plate["id"]
    )
    corrected_registration = next(
        result
        for result in corrected.json()["latest_analysis_run"]["document_ocr_results"]
        if result["id"] == registration["id"]
    )
    assert corrected_registration["raw_text"] == raw_ocr
    assert corrected_plate["ai_extracted_value"] == "51H-123.45"
    assert corrected_plate["confirmed_value"] == "51H-999.99"

    reviewed = client.post(
        f"/api/claims/{claim['id']}/analysis-runs/{run['id']}/ai-review",
        headers=adjuster_headers(client),
    )
    assert reviewed.status_code == 200

    locked = client.patch(
        f"/api/claims/{claim['id']}/analysis-runs/{run['id']}/extraction-fields/{plate['id']}",
        headers=adjuster_headers(client),
        json={"confirmed_value": "51H-000.00"},
    )
    assert locked.status_code == 409


def test_admin_can_start_workflow_analysis(client: TestClient):
    claim = prepare_claim_for_workflow_analysis(client)

    started = client.post(
        f"/api/claims/{claim['id']}/analysis-runs",
        headers=admin_headers(client),
    )

    assert started.status_code == 202


def test_workflow_analysis_preserves_successful_results_when_one_document_fails(client: TestClient):
    claim = prepare_claim_for_workflow_analysis(client, driver_license_filename="analysis-fail.jpg")

    client.post(
        f"/api/claims/{claim['id']}/analysis-runs",
        headers=adjuster_headers(client),
    )

    run = client.get(f"/api/claims/{claim['id']}", headers=adjuster_headers(client)).json()[
        "latest_analysis_run"
    ]
    assert run["status"] == "PARTIAL"
    assert run["damage_status"] == "COMPLETED"
    failed = next(
        item for item in run["document_analyses"] if item["document_type"] == "DRIVER_LICENSE"
    )
    assert failed["status"] == "FAILED"
    assert failed["warnings"] == ["analysis-fail.jpg: Mock OCR failed for this evidence image."]
    assert any(item["status"] == "COMPLETED" for item in run["document_analyses"])


def test_adjuster_can_correct_document_fields_then_run_structured_ai_review(client: TestClient, monkeypatch):
    claim = prepare_claim_for_workflow_analysis(client)
    client.post(
        f"/api/claims/{claim['id']}/analysis-runs",
        headers=adjuster_headers(client),
    )
    detail = client.get(f"/api/claims/{claim['id']}", headers=adjuster_headers(client)).json()
    run = detail["latest_analysis_run"]
    registration = next(
        item for item in run["document_analyses"] if item["document_type"] == "VEHICLE_REGISTRATION"
    )
    plate = next(field for field in registration["fields"] if field["key"] == "license_plate")

    corrected = client.patch(
        f"/api/claims/{claim['id']}/document-analyses/{registration['id']}/fields/{plate['id']}",
        headers=adjuster_headers(client),
        json={"reviewed_value": "51H-999.99"},
    )

    assert corrected.status_code == 200
    corrected_plate = next(
        field
        for document in corrected.json()["latest_analysis_run"]["document_analyses"]
        if document["id"] == registration["id"]
        for field in document["fields"]
        if field["id"] == plate["id"]
    )
    assert corrected_plate["original_ai_value"] == "51H-123.45"
    assert corrected_plate["reviewed_value"] == "51H-999.99"

    captured_context: dict[str, object] = {}
    original_generate = LlmCopilotService.generate

    def capture_normalized_input(self, input_data):
        captured_context.update(input_data.model_context())
        return original_generate(self, input_data)

    monkeypatch.setattr(LlmCopilotService, "generate", capture_normalized_input)

    reviewed = client.post(
        f"/api/claims/{claim['id']}/analysis-runs/{run['id']}/ai-review",
        headers=adjuster_headers(client),
    )

    assert reviewed.status_code == 200
    conclusion = reviewed.json()["latest_damage_analysis"]["copilot_conclusion"]
    assert 0 <= conclusion["validity_percentage"] <= 100
    assert conclusion["review_status"] == "REVIEW_REQUIRED"
    assert len(conclusion["evidence_references"]) == 5
    assert conclusion["summary"]
    assert captured_context["claim"] == {"id": claim["id"], "status": "REVIEW_REQUIRED"}
    assert captured_context["incident"]["location"] == "District 1, Ho Chi Minh City"
    registration_payload = next(
        item
        for item in captured_context["document_analysis"]
        if item["document_type"] == "VEHICLE_REGISTRATION"
    )
    assert next(
        field for field in registration_payload["fields"] if field["key"] == "license_plate"
    )["reviewed_value"] == "51H-999.99"


def test_ai_review_rejects_analysis_run_after_claim_inputs_change(client: TestClient):
    claim = prepare_claim_for_workflow_analysis(client)
    client.post(f"/api/claims/{claim['id']}/analysis-runs", headers=adjuster_headers(client))
    detail = client.get(f"/api/claims/{claim['id']}", headers=adjuster_headers(client)).json()
    run = detail["latest_analysis_run"]

    updated = client.patch(
        f"/api/claims/{claim['id']}/information",
        headers=adjuster_headers(client),
        json={
            "claimant_name": detail["claimant_name"],
            "vehicle": detail["vehicle"],
            "incident": {
                **detail["incident"],
                "location": "Thu Duc City, Ho Chi Minh City",
            },
        },
    )
    assert updated.status_code == 200
    assert updated.json()["latest_analysis_run"]["inputs_changed"] is True

    reviewed = client.post(
        f"/api/claims/{claim['id']}/analysis-runs/{run['id']}/ai-review",
        headers=adjuster_headers(client),
    )

    assert reviewed.status_code == 422
    assert reviewed.json() == {
        "detail": "Claim information or evidence changed; run analysis again"
    }


def test_human_review_requires_a_note_and_can_be_reverted_without_losing_history(client: TestClient):
    claim = prepare_claim_for_workflow_analysis(client)
    client.post(f"/api/claims/{claim['id']}/analysis-runs", headers=adjuster_headers(client))
    detail = client.get(f"/api/claims/{claim['id']}", headers=adjuster_headers(client)).json()
    run = detail["latest_analysis_run"]
    reviewed = client.post(
        f"/api/claims/{claim['id']}/analysis-runs/{run['id']}/ai-review",
        headers=adjuster_headers(client),
    ).json()
    conclusion_id = reviewed["latest_damage_analysis"]["copilot_conclusion"]["id"]

    missing_note = client.post(
        f"/api/claims/{claim['id']}/copilot-conclusions/{conclusion_id}/review",
        headers=adjuster_headers(client),
        json={"status": "APPROVED"},
    )
    assert missing_note.status_code == 422

    approved = client.post(
        f"/api/claims/{claim['id']}/copilot-conclusions/{conclusion_id}/review",
        headers=adjuster_headers(client),
        json={"status": "APPROVED", "comment": "Evidence is consistent after manual verification."},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "AI_APPROVED"

    rerun_before_revert = client.post(
        f"/api/claims/{claim['id']}/analysis-runs",
        headers=adjuster_headers(client),
    )
    assert rerun_before_revert.status_code == 422
    assert rerun_before_revert.json() == {
        "detail": "Revert the human review before running analysis again"
    }

    evidence_before_revert = approved.json()["evidence"][0]
    removal_before_revert = client.delete(
        f"/api/claims/{claim['id']}/evidence/{evidence_before_revert['id']}",
        headers=adjuster_headers(client),
    )
    assert removal_before_revert.status_code == 409

    reverted = client.post(
        f"/api/claims/{claim['id']}/copilot-conclusions/{conclusion_id}/review/revert",
        headers=adjuster_headers(client),
        json={"note": "Correct the registration plate and rerun the review."},
    )

    assert reverted.status_code == 200
    assert reverted.json()["status"] == "REVIEW_REQUIRED"
    history = reverted.json()["copilot_review_history"]
    assert len(history) == 1
    assert history[0]["comment"] == "Evidence is consistent after manual verification."
    assert history[0]["reverted_at"]
    assert history[0]["reverted_by"] == "adjuster@example.com"
    assert history[0]["revert_note"] == "Correct the registration plate and rerun the review."

    damage_evidence_id = next(
        item["id"]
        for item in reverted.json()["evidence"]
        if item["category"] == "VEHICLE_DAMAGE_IMAGE"
    )
    removed = client.delete(
        f"/api/claims/{claim['id']}/evidence/{damage_evidence_id}",
        headers=adjuster_headers(client),
    )
    assert removed.status_code == 200
    assert all(item["id"] != damage_evidence_id for item in removed.json()["evidence"])
    assert removed.json()["copilot_review_history"][0]["revert_note"]


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
            "group_id": None,
            "group_label": None,
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
        json={"status": "APPROVED", "comment": "The model result matches the submitted evidence."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "AI_APPROVED"
    assert response.json()["latest_damage_analysis"]["copilot_conclusion"]["review_history"] == [{
        "claim_id": claim["id"],
        "conclusion_id": conclusion["id"],
        "status": "APPROVED",
        "reason_category": None,
        "comment": "The model result matches the submitted evidence.",
        "reviewer": "adjuster@example.com",
        "reviewed_at": response.json()["latest_damage_analysis"]["copilot_conclusion"]["review_history"][0]["reviewed_at"],
        "reverted_at": None,
        "reverted_by": None,
        "revert_note": None,
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


def test_admin_can_review_an_ai_conclusion_and_a_conclusion_cannot_be_reviewed_twice(client: TestClient):
    claim, conclusion = create_reviewable_conclusion(client)

    admin_response = client.post(
        f"/api/claims/{claim['id']}/copilot-conclusions/{conclusion['id']}/review",
        headers=admin_headers(client),
        json={"status": "APPROVED", "comment": "Reviewed by administrator."},
    )
    assert admin_response.status_code == 200

    duplicate = client.post(
        f"/api/claims/{claim['id']}/copilot-conclusions/{conclusion['id']}/review",
        headers=adjuster_headers(client),
        json={"status": "APPROVED", "comment": "Duplicate review attempt."},
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "AI conclusion has already been reviewed"}
