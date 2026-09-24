import json
import logging
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator

from app.core.config import Settings
from app.models import CopilotConclusionStatus

AI_REVIEW_PROMPT_VERSION = "ai-review-v2"
AI_REVIEW_SCHEMA_VERSION = "ai-review-schema-v2"
MANUAL_ADJUSTER_REVIEW = "MANUAL_ADJUSTER_REVIEW"
logger = logging.getLogger(__name__)

AI_REVIEW_SYSTEM_PROMPT = """You are an insurance claim review assistant.
Summarize only the facts supplied in the JSON context. The deterministic assessment and
document consistency values are authoritative. Never infer missing values, invent damage,
prices, evidence, policy terms, claim outcomes, or legal conclusions. Reference prices are
informational only and are not repair costs, payouts, or guaranteed replacement costs.
Always state that a human adjuster must review the case. You support the adjuster; you do
not approve or reject the insurance claim. Return the required structured output only."""


class LlmGenerationError(Exception):
    pass


class AiReviewClaimFacts(BaseModel):
    claim_number: str
    status: str
    claimant_name: str


class AiReviewVehicleFacts(BaseModel):
    make: str
    model: str
    year: int
    license_plate: str | None = None
    vin: str | None = None


class AiReviewIncidentFacts(BaseModel):
    occurred_at: str | None = None
    location: str | None = None
    description: str | None = None


class AiReviewDocumentField(BaseModel):
    value: str | None = None
    consistency: str | None = None


class AiReviewDocument(BaseModel):
    fields: dict[str, AiReviewDocumentField] = Field(default_factory=dict)


class AiReviewDamageFinding(BaseModel):
    part: str | None = None
    damage_type: str | None = None
    area_percentage: float


class AiReviewDamage(BaseModel):
    assessment: str
    findings: list[AiReviewDamageFinding] = Field(default_factory=list)
    warning: str | None = None


class AiReviewReferencePrice(BaseModel):
    part: str
    amount: float | None = None
    currency: str | None = None
    source_name: str | None = None
    price_type: str
    status: str


class AiReviewContext(BaseModel):
    claim: AiReviewClaimFacts
    vehicle: AiReviewVehicleFacts
    incident: AiReviewIncidentFacts | None = None
    documents: dict[str, AiReviewDocument] = Field(default_factory=dict)
    damage: AiReviewDamage
    warnings: list[str] = Field(default_factory=list)
    reference_prices: list[AiReviewReferencePrice] = Field(default_factory=list)


class AiReviewStructuredResult(BaseModel):
    summary: str
    assessment_interpretation: str
    damaged_parts_summary: str
    document_consistency_summary: str
    warnings: list[str] = Field(default_factory=list)
    recommended_next_step: str
    human_review_required: bool = True

    @model_validator(mode="after")
    def require_human_review(self) -> "AiReviewStructuredResult":
        if not self.human_review_required:
            raise ValueError("AI Review must require a human adjuster")
        return self


@dataclass(frozen=True)
class CopilotInput:
    context: AiReviewContext

    def model_context(self) -> dict[str, object]:
        return self.context.model_dump(mode="json")


@dataclass(frozen=True)
class CopilotConclusionResult:
    status: CopilotConclusionStatus
    recommendation: str
    structured_review: AiReviewStructuredResult
    fallback_summary: str | None
    failure_reason: str | None
    prompt_version: str = AI_REVIEW_PROMPT_VERSION
    schema_version: str = AI_REVIEW_SCHEMA_VERSION

    @property
    def summary(self) -> str:
        return self.structured_review.summary


class LlmCopilotAdapter(Protocol):
    def generate_review(self, input_data: CopilotInput) -> AiReviewStructuredResult: ...


class DeterministicLlmCopilotAdapter:
    def generate_review(self, input_data: CopilotInput) -> AiReviewStructuredResult:
        context = input_data.context
        if context.damage.findings:
            damaged_parts_summary = ", ".join(
                (
                    f"{finding.part or 'unidentified vehicle area'}"
                    f" ({finding.damage_type or 'unspecified damage'}, "
                    f"{finding.area_percentage:g}%)"
                )
                for finding in context.damage.findings
            )
        else:
            damaged_parts_summary = "No normalized damaged parts were supplied."

        consistency_values = {
            field.consistency
            for document in context.documents.values()
            for field in document.fields.values()
            if field.consistency
        }
        if not consistency_values:
            document_summary = "Document consistency information is unavailable."
        elif consistency_values == {"MATCH"}:
            document_summary = "All comparable confirmed document fields match."
        else:
            statuses = ", ".join(sorted(consistency_values))
            document_summary = f"Confirmed document consistency statuses: {statuses}."

        warnings = [*context.warnings]
        if context.damage.warning:
            warnings.append(context.damage.warning)
        if context.reference_prices:
            warnings.append(
                "Reference prices are informational only and require adjuster verification."
            )
        summary = (
            f"The confirmed analysis supports a {context.damage.assessment} assessment. "
            f"{damaged_parts_summary} {document_summary} "
            "A human adjuster must review this case before any final decision."
        )
        return AiReviewStructuredResult(
            summary=summary,
            assessment_interpretation=(
                f"The deterministic damage assessment is {context.damage.assessment}."
            ),
            damaged_parts_summary=damaged_parts_summary,
            document_consistency_summary=document_summary,
            warnings=list(dict.fromkeys(warnings)),
            recommended_next_step=(
                "A human adjuster must verify the confirmed documents, vehicle damage, "
                "and any reference prices before making a decision."
            ),
            human_review_required=True,
        )


class UnavailableLlmCopilotAdapter:
    def __init__(self, reason: str):
        self.reason = reason

    def generate_review(self, input_data: CopilotInput) -> AiReviewStructuredResult:
        raise LlmGenerationError(self.reason)


class LangChainOpenAiAdapter:
    def __init__(self, base_url: str | None, api_key: str, model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def generate_review(self, input_data: CopilotInput) -> AiReviewStructuredResult:
        try:
            from langchain.messages import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI

            chat_options = {
                "model": self.model,
                "api_key": self.api_key,
                "temperature": 0,
                "reasoning_effort": "medium",
            }
            if self.base_url:
                chat_options["base_url"] = self.base_url
            model = ChatOpenAI(**chat_options)
            structured_model = model.with_structured_output(AiReviewStructuredResult)
            response = structured_model.invoke(
                [
                    SystemMessage(content=AI_REVIEW_SYSTEM_PROMPT),
                    HumanMessage(
                        content=json.dumps(
                            input_data.model_context(),
                            ensure_ascii=False,
                        )
                    ),
                ]
            )
            return AiReviewStructuredResult.model_validate(response)
        except Exception as error:
            logger.warning(
                "OpenAI AI Review generation failed for model %s (%s)",
                self.model,
                type(error).__name__,
            )
            raise LlmGenerationError(
                f"LLM generation failed ({type(error).__name__})."
            ) from error


class LlmCopilotService:
    def __init__(self, adapter: LlmCopilotAdapter):
        self.adapter = adapter

    def generate(self, input_data: CopilotInput) -> CopilotConclusionResult:
        fallback = DeterministicLlmCopilotAdapter().generate_review(input_data)
        try:
            review = self.adapter.generate_review(input_data)
        except Exception:
            logger.exception("AI review generation failed")
            return CopilotConclusionResult(
                status=CopilotConclusionStatus.LLM_UNAVAILABLE,
                recommendation=MANUAL_ADJUSTER_REVIEW,
                structured_review=fallback,
                fallback_summary=fallback.summary,
                failure_reason="LLM generation failed",
            )

        is_fallback = isinstance(self.adapter, DeterministicLlmCopilotAdapter)
        return CopilotConclusionResult(
            status=(
                CopilotConclusionStatus.FALLBACK
                if is_fallback
                else CopilotConclusionStatus.GENERATED
            ),
            recommendation=MANUAL_ADJUSTER_REVIEW,
            structured_review=review,
            fallback_summary=review.summary if is_fallback else None,
            failure_reason=None,
        )


def get_llm_copilot_adapter(settings: Settings) -> LlmCopilotAdapter:
    if settings.llm_mode == "mock":
        return DeterministicLlmCopilotAdapter()
    if not settings.openai_api_key:
        return UnavailableLlmCopilotAdapter("OPENAI_API_KEY is not configured")
    if not settings.openai_model:
        return UnavailableLlmCopilotAdapter("OPENAI_MODEL is not configured")
    return LangChainOpenAiAdapter(
        settings.llm_base_url,
        settings.openai_api_key,
        settings.openai_model,
    )
