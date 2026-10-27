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
    AiReviewGenerationResult,
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
        price_recommendation={"recommendation": "MANUAL_REVIEW", "rationale": "The adjuster must verify available prices."},
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
    assert captured["schema"] is AiReviewGenerationResult
    assert captured["structured_output_options"] == {
        "method": "json_schema",
        "include_raw": True,
        "strict": True,
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


def priced_input(assessment="REPAIR_LIKELY"):
    payload = build_input().model_context()
    payload["damage"]["assessment"] = assessment
    price = {"part_identity": "rear_bumper", "amount": 1200000, "currency": "VND",
             "source_name": "Demo catalog", "source_url": None, "price_type": "REPAIR_ESTIMATE",
             "retrieved_at": "2026-01-01T00:00:00Z", "status": "FOUND", "failure_reason": None}
    payload["pricing"] = {
        "currency": "VND",
        "repair_estimate": {"status": "COMPLETE", "total_amount": 1200000, "known_subtotal": 1200000, "priced_parts": 1, "total_parts": 1},
        "replacement_part_price": {"status": "COMPLETE", "total_amount": 4200000, "known_subtotal": 4200000, "priced_parts": 1, "total_parts": 1},
        "line_items": [{"part_identity": "rear_bumper", "repair_estimate": price,
                        "replacement_part_price": {**price, "amount": 4200000, "price_type": "REPLACEMENT_PART_PRICE"}}],
    }
    return CopilotInput(context=AiReviewContext.model_validate(payload))


@pytest.mark.parametrize("assessment,advice,expected", [
    ("REPAIR_LIKELY", "SUPPORTS_REPAIR", "SUPPORTS_REPAIR"),
    ("REPLACEMENT_LIKELY", "SUPPORTS_REPLACEMENT", "SUPPORTS_REPLACEMENT"),
    ("REPAIR_LIKELY", "MANUAL_REVIEW", "MANUAL_REVIEW"),
    ("REPAIR_LIKELY", "SUPPORTS_REPLACEMENT", "MANUAL_REVIEW"),
    ("MANUAL_INSPECTION_REQUIRED", "SUPPORTS_REPAIR", "MANUAL_REVIEW"),
])
def test_price_advice_respects_the_confirmed_assessment(assessment, advice, expected):
    input_data = priced_input(assessment)
    original = input_data.model_context()
    calls = []

    class Adapter:
        def generate_review(self, value):
            calls.append(value.model_context())
            return AiReviewStructuredResult.model_validate({**structured_review().model_dump(),
                "price_recommendation": {"recommendation": advice, "rationale": "Exact-match price evidence requires adjuster verification."}})

    result = LlmCopilotService(Adapter()).generate(input_data)
    assert len(calls) == 1
    assert calls[0] == original == input_data.model_context()
    assert result.status == "GENERATED"
    assert result.structured_review.price_recommendation.recommendation == expected
    assert set(result.structured_review.price_recommendation.model_dump()) == {"recommendation", "rationale"}
    assert result.structured_review.human_review_required is True
    assert result.recommendation == "MANUAL_ADJUSTER_REVIEW"


@pytest.mark.parametrize("invalid", [
    {"price_recommendation": {"recommendation": "SUPPORTS_REPAIR", "rationale": "Generated quote", "amount": 1}},
    {"price_recommendation": {"recommendation": "APPROVE_CLAIM", "rationale": "Approve"}},
    {"human_review_required": False},
])
def test_invalid_provider_price_output_preserves_review_fallback(invalid):
    class Adapter:
        def generate_review(self, value):
            return AiReviewGenerationResult.model_validate({**structured_review().model_dump(), **invalid})
    result = LlmCopilotService(Adapter()).generate(priced_input())
    assert result.status == "LLM_UNAVAILABLE"
    assert result.structured_review.price_recommendation.recommendation == "MANUAL_REVIEW"
    assert result.structured_review.human_review_required is True
    assert result.structured_review.damaged_parts_summary


@pytest.mark.parametrize("rationale", ["Repair costs 1 VND and replacement costs 2 VND.", "Approve the claim.", "Giá sửa chữa là một triệu đồng.", "Giá sửa chữa là một đồng."])
def test_model_written_amounts_or_claim_decisions_only_replace_pricing_advice(rationale):
    class Adapter:
        def generate_review(self, value):
            return AiReviewStructuredResult.model_validate({**structured_review().model_dump(),
                "price_recommendation": {"recommendation": "SUPPORTS_REPAIR", "rationale": rationale}})
    result = LlmCopilotService(Adapter()).generate(priced_input())
    assert result.status == "GENERATED"
    assert result.structured_review.summary == structured_review().summary
    assert result.structured_review.price_recommendation.recommendation == "MANUAL_REVIEW"
    assert rationale not in result.structured_review.price_recommendation.rationale


def test_historical_reviews_can_omit_price_advice_but_new_provider_output_cannot():
    historical = structured_review().model_dump(exclude={"price_recommendation"})
    assert AiReviewStructuredResult.model_validate(historical).price_recommendation is None
    with pytest.raises(ValueError):
        AiReviewGenerationResult.model_validate(historical)


def test_qualitative_vietnamese_prose_is_not_mistaken_for_monetary_amounts():
    rationale = "Chuyên viên đồng thời cần xác minh nguồn giá và tỷ lệ hư hại."
    class Adapter:
        def generate_review(self, value):
            return AiReviewStructuredResult.model_validate({**structured_review().model_dump(),
                "price_recommendation": {"recommendation": "SUPPORTS_REPAIR", "rationale": rationale}})
    result = LlmCopilotService(Adapter()).generate(priced_input())
    assert result.structured_review.price_recommendation.recommendation == "SUPPORTS_REPAIR"
    assert result.structured_review.price_recommendation.rationale == rationale
