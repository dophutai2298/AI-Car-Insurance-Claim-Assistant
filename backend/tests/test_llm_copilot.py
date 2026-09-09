from types import SimpleNamespace

from app.services.llm_copilot import (
    CopilotInput,
    CopilotSelection,
    CopilotSelectionResult,
    CopilotStructuredFinding,
    CopilotConclusionStatus,
    get_llm_copilot_adapter,
    LlmCopilotService,
    LlmGenerationError,
)


class SuccessfulAdapter:
    def generate_selection(self, input_data: CopilotInput) -> CopilotSelectionResult:
        return CopilotSelectionResult(
            CopilotConclusionStatus.GENERATED,
            CopilotSelection(finding_indexes=[0], include_reference_prices=False),
        )


class FailingAdapter:
    def generate_selection(self, input_data: CopilotInput) -> CopilotSelectionResult:
        raise LlmGenerationError("Provider request failed")


def build_input() -> CopilotInput:
    return CopilotInput(
        vehicle_summary="2022 Toyota Camry",
        assessment="REPLACEMENT_LIKELY",
        warning=None,
        findings=[
            CopilotStructuredFinding(
                vehicle_part="front_left_door",
                damage_type="severe_deformation",
                damage_percentage=72.0,
                confidence=0.92,
            )
        ],
        reference_prices=[],
    )


def test_llm_copilot_uses_only_adapter_selected_input_facts_in_its_summary():
    conclusion = LlmCopilotService(SuccessfulAdapter()).generate(build_input())

    assert conclusion.status == "GENERATED"
    assert "front_left_door at 72% damage" in conclusion.summary
    assert conclusion.recommendation == "MANUAL_ADJUSTER_REVIEW"


def test_llm_copilot_returns_a_fallback_when_the_adapter_fails():
    conclusion = LlmCopilotService(FailingAdapter()).generate(build_input())

    assert conclusion.status == "LLM_UNAVAILABLE"
    assert conclusion.fallback_summary
    assert conclusion.failure_reason == "Provider request failed"


def test_together_configuration_is_passed_to_the_langchain_openai_adapter(monkeypatch):
    captured: dict[str, object] = {}

    class StructuredModel:
        def invoke(self, messages):
            return {"finding_indexes": [0], "include_warning": False, "include_reference_prices": False}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def with_structured_output(self, schema):
            captured["schema"] = schema
            return StructuredModel()

    monkeypatch.setattr("langchain_openai.ChatOpenAI", FakeChatOpenAI)
    settings = SimpleNamespace(
        llm_mode="openai",
        llm_base_url="https://api.together.xyz/v1",
        openai_api_key="test-key",
        openai_model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    )

    result = get_llm_copilot_adapter(settings).generate_selection(build_input())

    assert captured["base_url"] == "https://api.together.xyz/v1"
    assert captured["api_key"] == "test-key"
    assert captured["model"] == "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
    assert captured["schema"] is CopilotSelection
    assert result.status is CopilotConclusionStatus.GENERATED
