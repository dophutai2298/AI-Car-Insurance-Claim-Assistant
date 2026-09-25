import logging
from types import SimpleNamespace

from app.services.llm_token_usage import log_llm_token_usage


def test_logs_langchain_usage_metadata_for_a_document(caplog):
    response = {
        "raw": SimpleNamespace(
            usage_metadata={
                "input_tokens": 125,
                "output_tokens": 24,
                "total_tokens": 149,
            },
            response_metadata={},
        )
    }

    with caplog.at_level(logging.INFO):
        log_llm_token_usage(
            enabled=True,
            operation="document_extraction",
            document_type="ID_CARD",
            model="gpt-test",
            response=response,
        )

    assert (
        "[LLM_TOKEN_USAGE] operation=document_extraction document=ID_CARD "
        "model=gpt-test input_tokens=125 output_tokens=24 total_tokens=149"
    ) in caplog.text


def test_logs_openai_response_metadata_as_a_fallback(caplog):
    response = SimpleNamespace(
        usage_metadata=None,
        response_metadata={
            "token_usage": {
                "prompt_tokens": 80,
                "completion_tokens": 12,
                "total_tokens": 92,
            }
        },
    )

    with caplog.at_level(logging.INFO):
        log_llm_token_usage(
            enabled=True,
            operation="document_field_validation",
            document_type="DRIVER_LICENSE",
            model="gpt-test",
            response=response,
            field_key="license_number",
        )

    assert "document=DRIVER_LICENSE" in caplog.text
    assert "field=license_number" in caplog.text
    assert "input_tokens=80 output_tokens=12 total_tokens=92" in caplog.text


def test_logs_usage_for_an_ai_review_claim(caplog):
    response = {
        "raw": SimpleNamespace(
            usage_metadata={
                "input_tokens": 480,
                "output_tokens": 120,
                "total_tokens": 600,
            },
            response_metadata={},
        )
    }

    with caplog.at_level(logging.INFO):
        log_llm_token_usage(
            enabled=True,
            operation="ai_review",
            claim_number="CLM-000001",
            model="gpt-test",
            response=response,
        )

    assert (
        "[LLM_TOKEN_USAGE] operation=ai_review claim=CLM-000001 model=gpt-test "
        "input_tokens=480 output_tokens=120 total_tokens=600"
    ) in caplog.text


def test_does_not_log_when_token_usage_logging_is_disabled(caplog):
    response = SimpleNamespace(
        usage_metadata={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
        response_metadata={},
    )

    with caplog.at_level(logging.INFO):
        log_llm_token_usage(
            enabled=False,
            operation="document_extraction",
            document_type="INSURANCE_POLICY",
            model="gpt-test",
            response=response,
        )

    assert "LLM_TOKEN_USAGE" not in caplog.text


def test_logs_unavailable_when_provider_omits_usage_metadata(caplog):
    response = SimpleNamespace(usage_metadata=None, response_metadata={})

    with caplog.at_level(logging.INFO):
        log_llm_token_usage(
            enabled=True,
            operation="document_extraction",
            document_type="VEHICLE_REGISTRATION",
            model="gpt-test",
            response=response,
        )

    assert (
        "[LLM_TOKEN_USAGE] operation=document_extraction document=VEHICLE_REGISTRATION "
        "model=gpt-test status=unavailable"
    ) in caplog.text
