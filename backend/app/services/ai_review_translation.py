import json
import logging
from typing import Protocol

from app.core.config import Settings
from app.services.llm_copilot import AiReviewStructuredResult
from app.services.llm_token_usage import log_llm_token_usage

AI_REVIEW_TRANSLATION_PROMPT_VERSION = "ai-review-translation-vi-v1"
AI_REVIEW_TRANSLATION_SCHEMA_VERSION = "ai-review-translation-schema-v1"

AI_REVIEW_TRANSLATION_SYSTEM_PROMPT = """
You are a professional Vietnamese localization editor for an insurance claim
review application.

Translate the supplied English AI Review fields into natural, concise
Vietnamese suitable for a Vietnamese insurance adjuster. Translate meaning,
not word order, while preserving every fact and limitation from the source.

Rules:
- Do not add, remove, summarize, reinterpret, or correct source facts.
- Preserve names, identifiers, dates, numbers, percentages, domain codes, and
  boolean values exactly.
- Keep each output field aligned with the corresponding input field.
- Translate every warning independently and preserve warning order.
- Keep human_review_required unchanged.
- Do not make an approval, rejection, coverage, fraud, legal, payout, repair,
  or replacement decision that is not present in the source.
- Return only the required structured output.
"""

logger = logging.getLogger(__name__)


class AiReviewTranslationError(Exception):
    pass


class AiReviewTranslationAdapter(Protocol):
    def translate(
        self, review: AiReviewStructuredResult
    ) -> AiReviewStructuredResult: ...


class UnavailableAiReviewTranslationAdapter:
    def __init__(self, reason: str):
        self.reason = reason

    def translate(self, review: AiReviewStructuredResult) -> AiReviewStructuredResult:
        raise AiReviewTranslationError(self.reason)


class LangChainOpenAiTranslationAdapter:
    def __init__(
        self,
        base_url: str | None,
        api_key: str,
        model: str,
        token_usage_logging_enabled: bool = False,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.token_usage_logging_enabled = token_usage_logging_enabled

    def translate(self, review: AiReviewStructuredResult) -> AiReviewStructuredResult:
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
            structured_model = ChatOpenAI(**chat_options).with_structured_output(
                AiReviewStructuredResult,
                method="json_schema",
                include_raw=True,
                strict=True,
            )
            response = structured_model.invoke(
                [
                    SystemMessage(content=AI_REVIEW_TRANSLATION_SYSTEM_PROMPT),
                    HumanMessage(
                        content=json.dumps(
                            review.model_dump(mode="json"), ensure_ascii=False
                        )
                    ),
                ]
            )
            log_llm_token_usage(
                enabled=self.token_usage_logging_enabled,
                operation="ai_review_translation",
                model=self.model,
                response=response,
            )
            parsed = response.get("parsed") if isinstance(response, dict) else response
            if parsed is None:
                raise AiReviewTranslationError(
                    "AI Review translation structured output parsing failed"
                )
            translated = AiReviewStructuredResult.model_validate(parsed)
            if translated.human_review_required != review.human_review_required:
                raise AiReviewTranslationError(
                    "AI Review translation changed a protected value"
                )
            return translated
        except AiReviewTranslationError:
            raise
        except Exception as error:
            logger.warning(
                "AI Review translation failed for model %s (%s)",
                self.model,
                type(error).__name__,
            )
            raise AiReviewTranslationError("AI Review translation failed") from error


def get_ai_review_translation_adapter(
    settings: Settings,
) -> AiReviewTranslationAdapter:
    if settings.llm_mode != "openai":
        return UnavailableAiReviewTranslationAdapter(
            "AI Review translation requires LLM_MODE=openai"
        )
    if not settings.openai_api_key:
        return UnavailableAiReviewTranslationAdapter(
            "OPENAI_API_KEY is not configured"
        )
    if not settings.openai_model:
        return UnavailableAiReviewTranslationAdapter("OPENAI_MODEL is not configured")
    return LangChainOpenAiTranslationAdapter(
        settings.llm_base_url,
        settings.openai_api_key,
        settings.openai_model,
        settings.llm_token_usage_log_enabled,
    )
