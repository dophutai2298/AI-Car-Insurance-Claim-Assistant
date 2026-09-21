import logging
from dataclasses import replace
from types import SimpleNamespace

from app.models import EvidenceCategory, FieldValidationStatus
from app.services.document_field_validation import (
    DocumentFieldValidationService,
    FIELD_CATALOG,
    FieldValidationError,
    FieldValidationSelection,
    LangChainOpenAiFieldValidationAdapter,
    ValidatedDocumentField,
)
from app.services.document_consistency import ClaimConsistencyService, ClaimFacts, normalize_for_comparison


def field(key: str, value: str | None, evidence_id: int = 1) -> ValidatedDocumentField:
    return ValidatedDocumentField(
        field_key=key,
        source_evidence_id=evidence_id,
        ocr_value=value,
        normalized_value=value,
        status="VALID" if value else "MISSING",
        confidence=0.95 if value else 0,
        summary="Fixture field",
        warnings=[],
        prompt_version="document-fields-v1",
    )


def test_langchain_field_validation_logs_usage_with_document_and_field(monkeypatch, caplog):
    class FakeChatOpenAI:
        def __init__(self, **options):
            pass

        def with_structured_output(self, schema, include_raw):
            assert schema is FieldValidationSelection
            assert include_raw is True
            return self

        def invoke(self, messages):
            return {
                "raw": SimpleNamespace(
                    usage_metadata={
                        "input_tokens": 55,
                        "output_tokens": 15,
                        "total_tokens": 70,
                    },
                    response_metadata={},
                ),
                "parsed": FieldValidationSelection(
                    ocr_value="Toyota",
                    normalized_value="Toyota",
                    status=FieldValidationStatus.VALID,
                    confidence=0.9,
                    summary="Vehicle make was found.",
                    warnings=[],
                ),
                "parsing_error": None,
            }

    monkeypatch.setattr("langchain_openai.ChatOpenAI", FakeChatOpenAI)
    adapter = LangChainOpenAiFieldValidationAdapter(
        None, "test-key", "test-model", token_usage_logging_enabled=True
    )
    definition = FIELD_CATALOG[EvidenceCategory.VEHICLE_REGISTRATION][2]
    definition = replace(definition, category=EvidenceCategory.VEHICLE_REGISTRATION)

    with caplog.at_level(logging.INFO):
        result = adapter.validate(definition, "Vehicle make: Toyota", {})

    assert result.normalized_value == "Toyota"
    assert "document=VEHICLE_REGISTRATION model=test-model field=vehicle_make" in caplog.text
    assert "input_tokens=55 output_tokens=15 total_tokens=70" in caplog.text


def test_consistency_normalization_handles_vietnamese_diacritics_case_whitespace_and_punctuation():
    assert normalize_for_comparison("  Nguyễn-Văn A. ") == "nguyenvana"
    assert normalize_for_comparison("ĐẶNG THỊ B") == "dangthib"


def test_consistency_service_returns_matches_and_preserves_display_values():
    results = ClaimConsistencyService().compare(
        ClaimFacts(claimant_name="Nguyen Van A", vehicle_make="TOYOTA", license_plate="51H 123-45"),
        [
            field("full_name", "Nguyễn Văn A", 10),
            field("vehicle_make", "Toyota", 11),
            field("license_plate", "51H-123.45", 11),
        ],
    )

    assert [result.status for result in results] == ["MATCH", "MATCH", "MATCH"]
    assert results[0].claim_value == "Nguyen Van A"
    assert results[0].document_value == "Nguyễn Văn A"


def test_consistency_service_returns_manual_review_warning_and_skips_legacy_missing_values():
    results = ClaimConsistencyService().compare(
        ClaimFacts(claimant_name="Mai Nguyen", vehicle_make="Toyota", license_plate="51H-123.45"),
        [field("owner_name", "Tran Van B"), field("vehicle_make", None), field("license_plate", "30A-999.99")],
    )

    assert [result.field_key for result in results] == ["owner_name", "license_plate"]
    assert all(result.status == "MISMATCH" for result in results)
    assert all("manual review" in result.explanation.lower() for result in results)


def test_consistency_service_compares_confirmed_extraction_field_names_and_brands():
    service = ClaimConsistencyService()
    claim = ClaimFacts(
        claimant_name="Nguyễn Văn A",
        vehicle_make="Toyota",
        license_plate="51H-123.45",
    )

    owner = service.compare_value(claim, "vehicle_owner", 10, "nguyen van a")
    brand = service.compare_value(claim, "vehicle_brand", 11, "TOYOTA")
    plate = service.compare_value(claim, "license_plate", 11, "51H 123-45")
    unrelated = service.compare_value(claim, "expiry_date", 12, "31/12/2030")
    missing = service.compare_value(claim, "vehicle_brand", 13, None)

    assert owner and owner.status == "MATCH"
    assert brand and brand.status == "MATCH"
    assert plate and plate.status == "MATCH"
    assert unrelated is None
    assert missing and missing.status == "UNAVAILABLE"


def test_field_validation_selects_a_dedicated_versioned_system_message_for_every_catalog_field():
    class CapturingAdapter:
        def __init__(self) -> None:
            self.calls = []

        def validate(self, definition, raw_ocr_text, claim_context):
            self.calls.append((definition, raw_ocr_text, claim_context))
            return FieldValidationSelection(
                ocr_value="Nguyen Van A",
                normalized_value="Nguyen Van A",
                status=FieldValidationStatus.VALID,
                confidence=0.94,
                summary="Name is present and readable.",
                warnings=[],
            )

    adapter = CapturingAdapter()
    results = DocumentFieldValidationService(adapter).validate_ocr_result(
        EvidenceCategory.ID_CARD,
        42,
        "Full name: Nguyen Van A",
        {"claimant_name": "Nguyen Van A"},
    )

    assert [result.field_key for result in results] == ["full_name", "identity_number", "date_of_birth"]
    assert all(result.source_evidence_id == 42 for result in results)
    assert all(call[0].prompt_version == "document-fields-v1" for call in adapter.calls)
    assert len({call[0].system_message for call in adapter.calls}) == 3
    assert adapter.calls[0][2] == {"expected_claim_value": "Nguyen Van A"}


def test_field_validation_isolates_provider_failure_and_preserves_deterministic_ocr_value():
    class PartiallyFailingAdapter:
        def validate(self, definition, raw_ocr_text, claim_context):
            if definition.field_key == "identity_number":
                raise FieldValidationError("Provider unavailable")
            return FieldValidationSelection(
                ocr_value=None,
                normalized_value=None,
                status=FieldValidationStatus.MISSING,
                confidence=0,
                summary="Field is not present.",
                warnings=[],
            )

    results = DocumentFieldValidationService(PartiallyFailingAdapter()).validate_ocr_result(
        EvidenceCategory.ID_CARD,
        7,
        "Identity number: 079203001234",
        {},
    )

    identity = next(result for result in results if result.field_key == "identity_number")
    assert identity.status == "LLM_UNAVAILABLE"
    assert identity.ocr_value == "079203001234"
    assert identity.normalized_value == "079203001234"
    assert identity.warnings == ["Provider unavailable"]
    assert all(result.field_key for result in results)


def test_field_validation_isolates_unexpected_adapter_failure_to_one_field():
    class UnexpectedFailureAdapter:
        def validate(self, definition, raw_ocr_text, claim_context):
            if definition.field_key == "identity_number":
                raise RuntimeError("Malformed provider response")
            return FieldValidationSelection(
                ocr_value=None,
                normalized_value=None,
                status=FieldValidationStatus.MISSING,
                confidence=0,
                summary="Field is not present.",
                warnings=[],
            )

    results = DocumentFieldValidationService(UnexpectedFailureAdapter()).validate_ocr_result(
        EvidenceCategory.ID_CARD,
        7,
        "Identity number: 079203001234",
        {},
    )

    identity = next(result for result in results if result.field_key == "identity_number")
    assert identity.status == "LLM_UNAVAILABLE"
    assert identity.ocr_value == "079203001234"
    assert identity.warnings == ["Field validation failed unexpectedly (RuntimeError)."]
