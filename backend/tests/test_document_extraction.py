import json
import logging
from pathlib import Path
from types import SimpleNamespace

from langchain.messages import HumanMessage, SystemMessage

from app.models import EvidenceCategory
from app.services.document_extraction import (
    DeterministicDocumentExtractionAdapter,
    DocumentExtractionService,
    DocumentExtractionDefinition,
    DocumentPromptResolver,
    DriverLicenseExtraction,
    IdentityCardExtraction,
    LangChainOpenAiDocumentExtractionAdapter,
    get_document_extraction_adapter,
)


def test_langchain_adapter_sends_system_and_human_messages_with_structured_schema(
    monkeypatch, caplog,
):
    captured: dict[str, object] = {}

    class FakeChatOpenAI:
        def __init__(self, **options):
            captured["options"] = options

        def with_structured_output(self, schema, method, include_raw):
            captured["schema"] = schema
            captured["method"] = method
            captured["include_raw"] = include_raw
            return self

        def invoke(self, messages):
            captured["messages"] = messages
            return {
                "raw": SimpleNamespace(
                    usage_metadata={
                        "input_tokens": 101,
                        "output_tokens": 17,
                        "total_tokens": 118,
                    },
                    response_metadata={},
                ),
                "parsed": {
                    "full_name": "Nguyen Van A",
                    "identity_number": "000123456789",
                    "date_of_birth": None,
                    "place_of_origin": None,
                    "expiry_date": None,
                },
                "parsing_error": None,
            }

    monkeypatch.setattr("langchain_openai.ChatOpenAI", FakeChatOpenAI)
    adapter = LangChainOpenAiDocumentExtractionAdapter(
        None, "test-key", "test-model", token_usage_logging_enabled=True
    )
    assert captured["options"] == {
        "model": "test-model",
        "api_key": "test-key",
        "temperature": 0,
        "timeout": 60.0,
        "max_retries": 0,
    }
    definition = DocumentExtractionDefinition(
        category=EvidenceCategory.ID_CARD,
        system_prompt="Extract identity fields only.",
        output_schema=IdentityCardExtraction,
    )

    with caplog.at_level(logging.INFO):
        result = adapter.extract(
            definition,
            "Identity number: 000123456789",
        )

    messages = captured["messages"]
    assert isinstance(messages, list)
    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == "Extract identity fields only."
    assert isinstance(messages[1], HumanMessage)
    assert json.loads(str(messages[1].content)) == {
        "raw_ocr_text": "Identity number: 000123456789"
    }
    assert "Mai Nguyen" not in str(messages[1].content)
    assert captured["schema"] is IdentityCardExtraction
    assert captured["method"] == "json_mode"
    assert captured["include_raw"] is True
    assert result.identity_number == "000123456789"
    assert "document=ID_CARD model=test-model" in caplog.text
    assert "input_tokens=101 output_tokens=17 total_tokens=118" in caplog.text


def test_missing_openai_credentials_produce_an_isolated_failed_extraction():
    class SettingsStub:
        llm_mode = "openai"
        llm_base_url = None
        openai_api_key = None
        openai_model = "gpt-test"

    service = DocumentExtractionService(get_document_extraction_adapter(SettingsStub()))

    outcome = service.extract(
        EvidenceCategory.ID_CARD,
        "Identity number: 000123456789",
    )

    assert outcome.status.value == "FAILED"
    assert outcome.fields == []
    assert outcome.warning == "OPENAI_API_KEY is not configured"


def test_identity_schema_normalizes_dates_and_keeps_leading_zeroes():
    extraction = IdentityCardExtraction(
        full_name="  Nguyen Van A  ",
        identity_number="000123456789",
        date_of_birth="2001-02-03",
        place_of_origin="  ",
        expiry_date="not-a-date",
    )

    assert extraction.full_name == "Nguyen Van A"
    assert extraction.identity_number == "000123456789"
    assert extraction.date_of_birth == "03/02/2001"
    assert extraction.place_of_origin is None
    assert extraction.expiry_date is None


def test_missing_prompt_resource_is_reported_as_an_extraction_failure(tmp_path: Path):
    service = DocumentExtractionService(
        DeterministicDocumentExtractionAdapter(),
        DocumentPromptResolver(tmp_path / "missing-prompts.md"),
    )

    outcome = service.extract(
        EvidenceCategory.ID_CARD,
        "Identity number: 000123456789",
    )

    assert outcome.status.value == "FAILED"
    assert outcome.fields == []
    assert outcome.warning == "Document extraction prompt resource is unavailable"


def test_prompt_resolver_selects_registration_and_driver_license_sections():
    resolver = DocumentPromptResolver()

    registration_prompt = resolver.resolve(EvidenceCategory.VEHICLE_REGISTRATION)
    driver_prompt = resolver.resolve(EvidenceCategory.DRIVER_LICENSE)

    assert "Vehicle Registration Certificate" in registration_prompt
    assert "`vehicle_owner`" in registration_prompt
    assert "`license_plate`" in registration_prompt
    assert "Driver License" in driver_prompt
    assert "`license_number`" in driver_prompt
    assert "`expiry_date`" in driver_prompt


def test_driver_license_schema_normalizes_expiry_and_keeps_leading_zeroes():
    extraction = DriverLicenseExtraction(
        license_number="001234567890",
        full_name="  Nguyen Van A  ",
        expiry_date="2030-12-31",
    )

    assert extraction.license_number == "001234567890"
    assert extraction.full_name == "Nguyen Van A"
    assert extraction.expiry_date == "31/12/2030"
