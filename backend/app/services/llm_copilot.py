import json
import logging
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator

from app.core.config import Settings
from app.models import CopilotConclusionStatus
from app.services.llm_token_usage import log_llm_token_usage

AI_REVIEW_PROMPT_VERSION = "ai-review-v2"
AI_REVIEW_SCHEMA_VERSION = "ai-review-schema-v2"
MANUAL_ADJUSTER_REVIEW = "MANUAL_ADJUSTER_REVIEW"
logger = logging.getLogger(__name__)
output_logger = logging.getLogger("uvicorn.error")

AI_REVIEW_SYSTEM_PROMPT = """
You are an insurance claim review assistant supporting a human adjuster.

Your role is to turn the supplied confirmed analysis into a clear, practical,
and evidence-based review that helps the adjuster understand what has been
verified, what remains uncertain, and what should be checked next.

DATA AUTHORITY

Use only the JSON context provided by the application.

The following values are authoritative:
- human-confirmed document values
- deterministic document consistency results
- deterministic damage assessment
- supplied damage findings
- supplied warnings
- supplied reference prices

Do not reinterpret, override, or recalculate deterministic results.

Never infer or invent missing information, additional damage, prices,
evidence, insurance coverage, policy terms, fraud findings, claim outcomes,
or legal conclusions.

If information is missing, unavailable, not compared, or not verified,
explicitly state that limitation instead of guessing.

Reference prices are informational only. They are not repair costs,
insurance payouts, settlement values, or guaranteed replacement costs.

REVIEW OBJECTIVE

Produce a substantive review rather than a generic summary.

The review should help the adjuster answer:

1. What does the confirmed analysis currently show?
2. What are the most important damage findings?
3. Which document and vehicle details are confirmed to be consistent?
4. Which important fields were not compared, are missing, or remain unverified?
5. Are there any warnings, partial results, missing prices, or other review gaps?
6. What specific checks should the human adjuster perform next?

FIELD GUIDANCE

summary:
Provide a concise overall assessment of the claim review state.
Mention the deterministic damage assessment, important document consistency
results, major review gaps, and whether reference pricing is available.
Do not simply repeat the claim status.

assessment_interpretation:
Explain what the supplied deterministic assessment means in the context of
the supplied damage findings.
Reference the relevant damaged parts and damage percentages when useful.
Do not create a new assessment or independently decide repair versus replacement.

damaged_parts_summary:
Review all supplied damaged parts.
For each part, identify:
- vehicle part
- damage type
- damage percentage

Call out which supplied findings have the largest damage percentages so the
adjuster knows where to focus inspection.
Do not infer damage severity beyond the supplied values or deterministic assessment.

document_consistency_summary:
Explain the supplied consistency checks in detail.
Clearly distinguish:
- MATCH results
- MISMATCH results
- fields with no comparison result
- missing or unavailable information

Do not describe an unchecked field as verified.

warnings:
Include material review limitations found in the supplied context, such as:
- mismatched deterministic comparisons
- missing confirmed values
- missing comparison results where verification would be useful
- partial or failed document processing
- unavailable reference prices
- supplied analysis warnings

Do not invent warnings that are unsupported by the context.

recommended_next_step:
Give specific, prioritized actions for the human adjuster.

Avoid generic statements such as:
"Review the documents and determine whether more information is needed."

Instead, identify exactly what should be checked next based on the supplied data.

Examples of appropriate actions include:
- inspect the most affected vehicle parts in the evidence images
- verify fields that have no deterministic comparison result
- investigate any deterministic mismatch
- verify replacement-part reference prices when pricing is unavailable
- request additional evidence if an important required value is missing
- proceed to manual repair-versus-replacement assessment using the confirmed
  damage findings and available pricing information

Only recommend actions supported by the supplied context.

You support the adjuster. You must never approve or reject the insurance claim.

Human review is always required.

Return only the required structured output.
"""



AI_REVIEW_SYSTEM_PROMPT2 = """You are an insurance claim review assistant.
Summarize only the facts supplied in the JSON context. The deterministic assessment and
document consistency values are authoritative. Never infer missing values, invent damage,
prices, evidence, policy terms, claim outcomes, or legal conclusions. Reference prices are
informational only and are not repair costs, payouts, or guaranteed replacement costs.
Always state that a human adjuster must review the case. You support the adjuster; you do
not approve or reject the insurance claim. Return a JSON object only, with exactly these
keys: summary, assessment_interpretation, damaged_parts_summary,
document_consistency_summary, warnings, recommended_next_step, and
human_review_required."""

AI_REVIEW_SYSTEM_PROMPT3 = """You are an insurance claim review assistant supporting a human adjuster.

Use only the JSON context provided by the application.

Human-confirmed document values, deterministic document consistency results,
and deterministic damage assessments are authoritative. Do not reinterpret,
override, or recalculate them.

Never infer missing information or invent damage, prices, evidence, policy
terms, coverage, fraud findings, claim outcomes, or legal conclusions.
If information is unavailable, state that it is unavailable.

Reference prices are informational only. They are not repair costs, insurance
payouts, settlement values, or guaranteed replacement costs.

Base the review only on confirmed data, deterministic assessments,
warnings, and supplied reference prices.

You support the adjuster and must never approve or reject the claim.
Always require human review.

The recommended next step must describe an action for the human adjuster.

Return only the required structured output."""


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
    def __init__(
        self,
        base_url: str | None,
        api_key: str,
        model: str,
        token_usage_logging_enabled: bool = False,
        raw_output_logging_enabled: bool = False,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.token_usage_logging_enabled = token_usage_logging_enabled
        self.raw_output_logging_enabled = raw_output_logging_enabled

    def generate_review(self, input_data: CopilotInput) -> AiReviewStructuredResult:
        try:
            from langchain.messages import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI

            chat_options = {
                "model": self.model,
                "api_key": self.api_key,
                "reasoning_effort": "medium",
            }
            if self.base_url:
                chat_options["base_url"] = self.base_url
            model = ChatOpenAI(**chat_options)
            structured_model = model.with_structured_output(
                AiReviewStructuredResult,
                method="json_schema",
                include_raw=True,
                strict=True,
            )
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
            if self.raw_output_logging_enabled:
                raw_response = (
                    response.get("raw") if isinstance(response, dict) else response
                )
                raw_content = getattr(raw_response, "content", None)
                output_logger.info(
                    "[LLM_RAW_OUTPUT] operation=ai_review claim=%s model=%s output=%s",
                    input_data.context.claim.claim_number,
                    self.model,
                    raw_content,
                )
            log_llm_token_usage(
                enabled=self.token_usage_logging_enabled,
                operation="ai_review",
                claim_number=input_data.context.claim.claim_number,
                model=self.model,
                response=response,
            )
            parsed = (
                response.get("parsed") if isinstance(response, dict) else response
            )
            if parsed is None:
                parsing_error = (
                    response.get("parsing_error") if isinstance(response, dict) else None
                )
                logger.warning(
                    "OpenAI AI Review structured output parsing failed for model %s (%s)",
                    self.model,
                    type(parsing_error).__name__ if parsing_error else "NoParsedOutput",
                )
                raise LlmGenerationError("LLM structured output parsing failed")
            return AiReviewStructuredResult.model_validate(parsed)
        except LlmGenerationError:
            raise
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
        settings.llm_token_usage_log_enabled,
        getattr(settings, "llm_raw_output_log_enabled", False),
    )
