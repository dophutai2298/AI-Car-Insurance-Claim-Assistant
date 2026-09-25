import json
import logging
from types import SimpleNamespace

import pytest

from app.services.llm_copilot import (
    AI_REVIEW_PROMPT_VERSION,
    AI_REVIEW_SCHEMA_VERSION,
    AiReviewClaimFacts,
    AiReviewContext,
    AiReviewDamage,
    AiReviewDamageFinding,
    AiReviewDocument,
    AiReviewDocumentField,
    AiReviewIncidentFacts,
    AiReviewReferencePrice,
    AiReviewStructuredResult,
    AiReviewVehicleFacts,
    CopilotInput,
    LlmCopilotService,
    LlmGenerationError,
    get_llm_copilot_adapter,
)


def structured_review(summary: str = "The confirmed claim requires manual review"):
    return AiReviewStructuredResult(
        summary=summary,
        assessment_interpretation="The deterministic assessment is REPAIR_LIKELY.",
        damaged_parts_summary="Rear bumper dent affects 32.5% of the part.",
        document_consistency_summary="All comparable confirmed fields match.",
        warnings=[],
        recommended_next_step="An adjuster must verify the evidence and reference price.",
        human_review_required=True,
    )


class SuccessfulAdapter:
    def generate_review(self, input_data: CopilotInput) -> AiReviewStructuredResult:
        return structured_review()


class FailingAdapter:
    def generate_review(self, input_data: CopilotInput) -> AiReviewStructuredResult:
        raise LlmGenerationError("Provider request failed")


def build_input() -> CopilotInput:
    return CopilotInput(
        context=AiReviewContext(
            claim=AiReviewClaimFacts(
                claim_number="CLM-000001",
                status="REVIEW_REQUIRED",
                claimant_name="Mai Nguyen",
            ),
            vehicle=AiReviewVehicleFacts(
                make="Toyota",
                model="Camry",
                year=2022,
                license_plate="51H-123.45",
                vin=None,
            ),
            incident=AiReviewIncidentFacts(
                occurred_at="2026-09-08T00:00:00Z",
                location="District 1, Ho Chi Minh City",
                description="Rear impact.",
            ),
            documents={
                "ID_CARD": AiReviewDocument(
                    fields={
                        "full_name": AiReviewDocumentField(
                            value="Mai Nguyen",
                            consistency="MATCH",
                        )
                    }
                )
            },
            damage=AiReviewDamage(
                assessment="REPAIR_LIKELY",
                findings=[
                    AiReviewDamageFinding(
                        part="rear_bumper",
                        damage_type="dent",
                        area_percentage=32.5,
                    )
                ],
                warning=None,
            ),
            warnings=[],
            reference_prices=[
                AiReviewReferencePrice(
                    part="rear_bumper",
                    amount=250.0,
                    currency="USD",
                    price_type="REFERENCE_OEM_PART_PRICE",
                    status="FOUND",
                )
            ],
        )
    )


def test_ai_review_context_contains_only_curated_review_facts():
    context = build_input().model_context()
    serialized = json.dumps(context)

    assert context["claim"]["claim_number"] == "CLM-000001"
    assert context["documents"]["ID_CARD"]["fields"]["full_name"] == {
        "value": "Mai Nguyen",
        "consistency": "MATCH",
    }
    assert context["damage"]["findings"] == [
        {
            "part": "rear_bumper",
            "damage_type": "dent",
            "area_percentage": 32.5,
        }
    ]
    for excluded in (
        "content_url",
        "source_evidence_id",
        "annotated_evidence_id",
        "raw_text",
        "adapter_metadata",
        "pixels",
        "confidence",
        "source_url",
    ):
        assert excluded not in serialized


def test_llm_copilot_returns_structured_provider_result():
    conclusion = LlmCopilotService(SuccessfulAdapter()).generate(build_input())

    assert conclusion.status == "GENERATED"
    assert conclusion.summary == "The confirmed claim requires manual review"
    assert conclusion.structured_review.human_review_required is True
    assert conclusion.prompt_version == AI_REVIEW_PROMPT_VERSION
    assert conclusion.schema_version == AI_REVIEW_SCHEMA_VERSION
    assert conclusion.recommendation == "MANUAL_ADJUSTER_REVIEW"


def test_llm_copilot_returns_same_structured_shape_when_provider_fails():
    conclusion = LlmCopilotService(FailingAdapter()).generate(build_input())

    assert conclusion.status == "LLM_UNAVAILABLE"
    assert conclusion.fallback_summary
    assert conclusion.failure_reason == "LLM generation failed"
    assert conclusion.structured_review.human_review_required is True
    assert conclusion.structured_review.damaged_parts_summary
    assert conclusion.structured_review.document_consistency_summary == (
        "All comparable confirmed document fields match."
    )
    assert conclusion.structured_review.warnings == [
        "Reference prices are informational only and require adjuster verification."
    ]


def test_openai_adapter_uses_langchain_messages_typed_output_and_logs_usage(monkeypatch, caplog):
    captured: dict[str, object] = {}

    class StructuredModel:
        def invoke(self, messages):
            captured["messages"] = messages
            return {
                "raw": SimpleNamespace(
                    usage_metadata={
                        "input_tokens": 480,
                        "output_tokens": 120,
                        "total_tokens": 600,
                    },
                    response_metadata={},
                ),
                "parsed": structured_review("OpenAI structured summary"),
                "parsing_error": None,
            }

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def with_structured_output(self, schema, **kwargs):
            captured["schema"] = schema
            captured["structured_output_options"] = kwargs
            return StructuredModel()

    monkeypatch.setattr("langchain_openai.ChatOpenAI", FakeChatOpenAI)
    settings = SimpleNamespace(
        llm_mode="openai",
        llm_base_url=None,
        openai_api_key="test-key",
        openai_model="gpt-5.6-luna",
        llm_token_usage_log_enabled=True,
    )

    with caplog.at_level(logging.INFO):
        result = get_llm_copilot_adapter(settings).generate_review(build_input())

    assert "base_url" not in captured
    assert captured["api_key"] == "test-key"
    assert captured["model"] == "gpt-5.6-luna"
    assert captured["schema"] is AiReviewStructuredResult
    assert captured["structured_output_options"] == {
        "method": "json_mode",
        "include_raw": True,
    }
    messages = captured["messages"]
    assert [type(message).__name__ for message in messages] == [
        "SystemMessage",
        "HumanMessage",
    ]
    assert "human adjuster" in messages[0].content.lower()
    assert json.loads(messages[1].content) == build_input().model_context()
    assert result.summary == "OpenAI structured summary"
    assert result.human_review_required is True
    assert (
        "[LLM_TOKEN_USAGE] operation=ai_review claim=CLM-000001 model=gpt-5.6-luna "
        "input_tokens=480 output_tokens=120 total_tokens=600"
    ) in caplog.text


def test_openai_adapter_reports_a_provider_structured_output_parsing_failure(monkeypatch, caplog):
    class StructuredModel:
        def invoke(self, messages):
            return {
                "raw": SimpleNamespace(usage_metadata=None, response_metadata={}),
                "parsed": None,
                "parsing_error": ValueError("Provider returned invalid JSON"),
            }

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            pass

        def with_structured_output(self, schema, **kwargs):
            return StructuredModel()

    monkeypatch.setattr("langchain_openai.ChatOpenAI", FakeChatOpenAI)
    settings = SimpleNamespace(
        llm_mode="openai",
        llm_base_url=None,
        openai_api_key="test-key",
        openai_model="nvidia/nemotron-3-ultra-550b-a55b:free",
        llm_token_usage_log_enabled=True,
    )

    with caplog.at_level(logging.WARNING), pytest.raises(
        LlmGenerationError,
        match="structured output parsing failed",
    ):
        get_llm_copilot_adapter(settings).generate_review(build_input())

    assert "structured output parsing failed" in caplog.text
