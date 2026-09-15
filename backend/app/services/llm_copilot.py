import json
from dataclasses import asdict, dataclass
from typing import Protocol

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.models import CopilotConclusionStatus

MANUAL_ADJUSTER_REVIEW = "MANUAL_ADJUSTER_REVIEW"


class LlmGenerationError(Exception):
    pass


@dataclass(frozen=True)
class CopilotStructuredFinding:
    vehicle_part: str | None
    damage_type: str | None
    damage_percentage: float
    confidence: float


@dataclass(frozen=True)
class CopilotReferencePrice:
    part_identity: str
    amount: float | None
    currency: str | None
    source_name: str | None
    source_url: str | None
    price_type: str
    status: str


@dataclass(frozen=True)
class CopilotInput:
    vehicle_summary: str
    assessment: str
    warning: str | None
    findings: list[CopilotStructuredFinding]
    reference_prices: list[CopilotReferencePrice]
    claim: dict[str, object] | None = None
    vehicle: dict[str, object] | None = None
    claimant: dict[str, object] | None = None
    incident: dict[str, object] | None = None
    document_analysis: list[dict[str, object]] | None = None
    warnings: list[str] | None = None
    evidence_references: list[dict[str, object]] | None = None

    def model_context(self) -> dict[str, object]:
        return {
            "vehicle_summary": self.vehicle_summary,
            "assessment": self.assessment,
            "warning": self.warning,
            "findings": [asdict(finding) for finding in self.findings],
            "reference_prices": [asdict(price) for price in self.reference_prices],
            "claim": self.claim,
            "vehicle": self.vehicle,
            "claimant": self.claimant,
            "incident": self.incident,
            "document_analysis": self.document_analysis or [],
            "warnings": self.warnings or [],
            "evidence_references": self.evidence_references or [],
        }


@dataclass(frozen=True)
class CopilotConclusionResult:
    status: CopilotConclusionStatus
    recommendation: str
    summary: str
    fallback_summary: str | None
    failure_reason: str | None


class CopilotSelection(BaseModel):
    finding_indexes: list[int] = Field(default_factory=list)
    include_warning: bool = False
    include_reference_prices: bool = False


@dataclass(frozen=True)
class CopilotSelectionResult:
    status: CopilotConclusionStatus
    selection: CopilotSelection


class LlmCopilotAdapter(Protocol):
    def generate_selection(self, input_data: CopilotInput) -> CopilotSelectionResult: ...


class DeterministicLlmCopilotAdapter:
    def generate_selection(self, input_data: CopilotInput) -> CopilotSelectionResult:
        return CopilotSelectionResult(
            status=CopilotConclusionStatus.FALLBACK,
            selection=CopilotSelection(
                finding_indexes=list(range(len(input_data.findings))),
                include_warning=input_data.warning is not None,
                include_reference_prices=bool(input_data.reference_prices),
            ),
        )


class UnavailableLlmCopilotAdapter:
    def __init__(self, reason: str):
        self.reason = reason

    def generate_selection(self, input_data: CopilotInput) -> CopilotSelectionResult:
        raise LlmGenerationError(self.reason)


class LangChainOpenAiAdapter:
    def __init__(self, base_url: str | None, api_key: str, model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def generate_selection(self, input_data: CopilotInput) -> CopilotSelectionResult:
        try:
            from langchain_openai import ChatOpenAI

            chat_options = {
                "model": self.model,
                "api_key": self.api_key,
                "temperature": 0,
            }
            if self.base_url:
                chat_options["base_url"] = self.base_url
            model = ChatOpenAI(**chat_options)
            structured_model = model.with_structured_output(CopilotSelection)
            response = structured_model.invoke(
                [
                    (
                        "system",
                        "You are an insurance claim copilot. Select only indexes from the supplied findings to highlight. Select whether the supplied warning and supplied reference prices should be included. Do not create findings, facts, costs, outcomes, or approvals.",
                    ),
                    ("human", json.dumps(input_data.model_context())),
                ]
            )
        except Exception as error:
            raise LlmGenerationError("LLM generation failed") from error

        try:
            selection = CopilotSelection.model_validate(response)
        except Exception as error:
            raise LlmGenerationError("LLM returned an invalid structured selection") from error
        return CopilotSelectionResult(CopilotConclusionStatus.GENERATED, selection)


class LlmCopilotService:
    def __init__(self, adapter: LlmCopilotAdapter):
        self.adapter = adapter

    def generate(self, input_data: CopilotInput) -> CopilotConclusionResult:
        fallback = DeterministicLlmCopilotAdapter().generate_selection(input_data)
        fallback_summary = self._summary_from_selection(input_data, fallback.selection)
        try:
            result = self.adapter.generate_selection(input_data)
        except Exception as error:
            return CopilotConclusionResult(
                status=CopilotConclusionStatus.LLM_UNAVAILABLE,
                recommendation=MANUAL_ADJUSTER_REVIEW,
                summary=fallback_summary,
                fallback_summary=fallback_summary,
                failure_reason=str(error) or "LLM generation failed",
            )

        return CopilotConclusionResult(
            status=result.status,
            recommendation=MANUAL_ADJUSTER_REVIEW,
            summary=self._summary_from_selection(input_data, result.selection),
            fallback_summary=fallback_summary if result.status is CopilotConclusionStatus.FALLBACK else None,
            failure_reason=None,
        )

    @staticmethod
    def _summary_from_selection(input_data: CopilotInput, selection: CopilotSelection) -> str:
        selected_findings = [
            input_data.findings[index]
            for index in selection.finding_indexes
            if 0 <= index < len(input_data.findings)
        ]
        if selected_findings:
            finding_text = ", ".join(
                f"{finding.vehicle_part or 'an unidentified vehicle area'} at {finding.damage_percentage:g}% damage"
                for finding in selected_findings
            )
            summary = f"Normalized findings support a {input_data.assessment} assessment: {finding_text}."
        else:
            summary = f"No normalized damage finding was selected for the {input_data.assessment} assessment."
        if selection.include_reference_prices and input_data.reference_prices:
            summary += " Reference part price information is available."
        if selection.include_warning and input_data.warning:
            summary += f" Warning: {input_data.warning}"
        return f"{summary} An adjuster must review this case before any final decision."


def get_llm_copilot_adapter(settings: Settings) -> LlmCopilotAdapter:
    if settings.llm_mode == "mock":
        return DeterministicLlmCopilotAdapter()
    if not settings.openai_api_key:
        return UnavailableLlmCopilotAdapter("OPENAI_API_KEY is not configured")
    if not settings.openai_model:
        return UnavailableLlmCopilotAdapter("OPENAI_MODEL is not configured")
    return LangChainOpenAiAdapter(settings.llm_base_url, settings.openai_api_key, settings.openai_model)
