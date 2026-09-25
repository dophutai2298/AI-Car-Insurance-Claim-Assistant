from dataclasses import dataclass, replace
import json
import logging
import re
from typing import Protocol

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.models import EvidenceCategory, FieldValidationStatus
from app.services.llm_token_usage import log_llm_token_usage


PROMPT_VERSION = "document-fields-v1"
logger = logging.getLogger(__name__)


def _system_message(field_key: str, expected_value: str, normalization: str) -> str:
    return (
        f"You validate only the '{field_key}' field in OCR text from an insurance claim document. "
        f"Expected value: {expected_value}. Normalization: {normalization}. "
        "Extract only a value supported by the OCR text; return null when absent or unreadable. "
        "Return the required structured validation fields and concise warnings. Never invent a value, "
        "approve or reject a claim, interpret legal coverage, or make a payout decision."
    )


@dataclass(frozen=True)
class DocumentFieldDefinition:
    field_key: str
    label: str
    aliases: tuple[str, ...]
    system_message: str
    prompt_version: str = PROMPT_VERSION
    category: EvidenceCategory | None = None


def _field(
    field_key: str,
    label: str,
    aliases: tuple[str, ...],
    expected: str,
    normalization: str,
) -> DocumentFieldDefinition:
    return DocumentFieldDefinition(
        field_key,
        label,
        aliases,
        _system_message(field_key, expected, normalization),
    )


FIELD_CATALOG: dict[EvidenceCategory, tuple[DocumentFieldDefinition, ...]] = {
    EvidenceCategory.ID_CARD: (
        _field(
            "full_name",
            "Full name",
            ("full name", "name", "ho va ten"),
            "the card holder's complete personal name",
            "trim whitespace and preserve the readable display name",
        ),
        _field(
            "identity_number",
            "Identity number",
            ("identity number", "id number", "so cccd", "so cmnd"),
            "the government identity number",
            "remove formatting spaces while preserving letters and digits",
        ),
        _field(
            "date_of_birth",
            "Date of birth",
            ("date of birth", "dob", "ngay sinh"),
            "the holder's date of birth",
            "normalize an unambiguous date to YYYY-MM-DD",
        ),
    ),
    EvidenceCategory.INSURANCE_POLICY: (
        _field(
            "policy_number",
            "Policy number",
            ("policy number", "policy no", "so hop dong"),
            "the insurance policy identifier",
            "trim whitespace and preserve meaningful letters, digits, and separators",
        ),
        _field(
            "insured_name",
            "Insured name",
            ("insured name", "policy holder", "nguoi duoc bao hiem"),
            "the insured person's complete name",
            "trim whitespace and preserve the readable display name",
        ),
        _field(
            "coverage_end",
            "Coverage end",
            ("coverage end", "expiry date", "valid until", "ngay het han"),
            "the policy coverage end date",
            "normalize an unambiguous date to YYYY-MM-DD",
        ),
    ),
    EvidenceCategory.VEHICLE_REGISTRATION: (
        _field(
            "owner_name",
            "Owner name",
            ("owner name", "registered owner", "chu xe"),
            "the registered vehicle owner's complete name",
            "trim whitespace and preserve the readable display name",
        ),
        _field(
            "license_plate",
            "License plate",
            ("license plate", "registration number", "bien so"),
            "the vehicle registration plate",
            "uppercase and remove cosmetic whitespace while preserving readable separators",
        ),
        _field(
            "vehicle_make",
            "Vehicle make",
            ("vehicle make", "make", "brand", "nhan hieu"),
            "the vehicle manufacturer",
            "trim whitespace and use the manufacturer display name",
        ),
    ),
    EvidenceCategory.DRIVER_LICENSE: (
        _field(
            "license_number",
            "License number",
            ("license number", "licence number", "so gplx"),
            "the driver license identifier",
            "remove formatting spaces while preserving letters and digits",
        ),
        _field(
            "holder_name",
            "Holder name",
            ("holder name", "full name", "ho va ten"),
            "the license holder's complete name",
            "trim whitespace and preserve the readable display name",
        ),
        _field(
            "license_class",
            "License class",
            ("license class", "class", "hang"),
            "the authorized driver license class",
            "uppercase and remove cosmetic whitespace",
        ),
    ),
}


class FieldValidationSelection(BaseModel):
    ocr_value: str | None
    normalized_value: str | None
    status: FieldValidationStatus
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(min_length=1, max_length=500)
    warnings: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class ValidatedDocumentField:
    field_key: str
    source_evidence_id: int
    ocr_value: str | None
    normalized_value: str | None
    status: FieldValidationStatus
    confidence: float
    summary: str
    warnings: list[str]
    prompt_version: str = PROMPT_VERSION


class FieldValidationError(Exception):
    pass


class DocumentFieldValidationAdapter(Protocol):
    def validate(
        self,
        definition: DocumentFieldDefinition,
        raw_ocr_text: str,
        claim_context: dict[str, str],
    ) -> FieldValidationSelection: ...


def _extract_catalog_value(definition: DocumentFieldDefinition, raw_ocr_text: str) -> str | None:
    for line in raw_ocr_text.splitlines():
        for alias in definition.aliases:
            match = re.match(rf"\s*{re.escape(alias)}\s*[:\-]\s*(.+?)\s*$", line, re.IGNORECASE)
            if match:
                return match.group(1).strip() or None
    return None


class DeterministicFieldValidationAdapter:
    def validate(
        self,
        definition: DocumentFieldDefinition,
        raw_ocr_text: str,
        claim_context: dict[str, str],
    ) -> FieldValidationSelection:
        value = _extract_catalog_value(definition, raw_ocr_text)
        if value is None:
            return FieldValidationSelection(
                ocr_value=None,
                normalized_value=None,
                status=FieldValidationStatus.MISSING,
                confidence=0,
                summary=f"{definition.label} was not found in OCR text.",
                warnings=["Manual review is required when this field is expected."],
            )
        return FieldValidationSelection(
            ocr_value=value,
            normalized_value=value,
            status=FieldValidationStatus.VALID,
            confidence=0.85,
            summary=f"{definition.label} was extracted from OCR text.",
            warnings=[],
        )


class UnavailableFieldValidationAdapter:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def validate(
        self,
        definition: DocumentFieldDefinition,
        raw_ocr_text: str,
        claim_context: dict[str, str],
    ) -> FieldValidationSelection:
        raise FieldValidationError(self.reason)


class LangChainOpenAiFieldValidationAdapter:
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

    def validate(
        self,
        definition: DocumentFieldDefinition,
        raw_ocr_text: str,
        claim_context: dict[str, str],
    ) -> FieldValidationSelection:
        try:
            from langchain_openai import ChatOpenAI

            options: dict[str, object] = {
                "model": self.model,
                "api_key": self.api_key,
                "temperature": 0,
                "reasoning_effort": "medium",
            }
            if self.base_url:
                options["base_url"] = self.base_url
            model = ChatOpenAI(**options).with_structured_output(
                FieldValidationSelection, include_raw=True
            )
            payload = {
                "prompt_version": definition.prompt_version,
                "field_key": definition.field_key,
                "raw_ocr_text": raw_ocr_text,
                "claim_context": claim_context,
            }
            response = model.invoke(
                [
                    ("system", definition.system_message),
                    ("human", json.dumps(payload, ensure_ascii=False)),
                ]
            )
            log_llm_token_usage(
                enabled=self.token_usage_logging_enabled,
                operation="document_field_validation",
                document_type=definition.category.value if definition.category else "UNKNOWN",
                model=self.model,
                response=response,
                field_key=definition.field_key,
            )
            parsed = response.get("parsed") if isinstance(response, dict) else None
            return FieldValidationSelection.model_validate(parsed)
        except Exception as error:
            logger.warning(
                "OpenAI document field validation failed for %s using %s (%s)",
                definition.field_key,
                self.model,
                type(error).__name__,
            )
            raise FieldValidationError(
                f"Field validation unavailable ({type(error).__name__})."
            ) from error


class DocumentFieldValidationService:
    def __init__(self, adapter: DocumentFieldValidationAdapter) -> None:
        self.adapter = adapter

    def validate_ocr_result(
        self,
        category: EvidenceCategory,
        source_evidence_id: int,
        raw_ocr_text: str,
        claim_information: dict[str, str],
    ) -> list[ValidatedDocumentField]:
        results: list[ValidatedDocumentField] = []
        for catalog_definition in FIELD_CATALOG[category]:
            definition = replace(catalog_definition, category=category)
            claim_context = self._claim_context(definition.field_key, claim_information)
            try:
                selection = self.adapter.validate(definition, raw_ocr_text, claim_context)
                if selection.ocr_value and selection.ocr_value.casefold() not in raw_ocr_text.casefold():
                    raise FieldValidationError("LLM returned a value not present in OCR text.")
                results.append(ValidatedDocumentField(
                    field_key=definition.field_key,
                    source_evidence_id=source_evidence_id,
                    ocr_value=selection.ocr_value,
                    normalized_value=selection.normalized_value,
                    status=selection.status,
                    confidence=selection.confidence,
                    summary=selection.summary,
                    warnings=selection.warnings,
                    prompt_version=definition.prompt_version,
                ))
            except FieldValidationError as error:
                results.append(
                    self._unavailable_result(
                        definition, source_evidence_id, raw_ocr_text, str(error)
                    )
                )
            except Exception as error:
                logger.exception("Unexpected field validation error for %s", definition.field_key)
                results.append(
                    self._unavailable_result(
                        definition,
                        source_evidence_id,
                        raw_ocr_text,
                        f"Field validation failed unexpectedly ({type(error).__name__}).",
                    )
                )
        return results

    @staticmethod
    def _unavailable_result(
        definition: DocumentFieldDefinition,
        source_evidence_id: int,
        raw_ocr_text: str,
        warning: str,
    ) -> ValidatedDocumentField:
        fallback_value = _extract_catalog_value(definition, raw_ocr_text)
        return ValidatedDocumentField(
            field_key=definition.field_key,
            source_evidence_id=source_evidence_id,
            ocr_value=fallback_value,
            normalized_value=fallback_value,
            status=FieldValidationStatus.LLM_UNAVAILABLE,
            confidence=0,
            summary=(
                f"{definition.label} requires manual review because LLM validation "
                "is unavailable."
            ),
            warnings=[warning],
            prompt_version=definition.prompt_version,
        )

    @staticmethod
    def _claim_context(field_key: str, claim_information: dict[str, str]) -> dict[str, str]:
        if field_key in {"full_name", "insured_name", "owner_name", "holder_name"}:
            expected = claim_information.get("claimant_name")
        elif field_key == "vehicle_make":
            expected = claim_information.get("vehicle_make")
        elif field_key == "license_plate":
            expected = claim_information.get("license_plate")
        else:
            expected = None
        return {"expected_claim_value": expected} if expected else {}


def get_document_field_validation_adapter(settings: Settings) -> DocumentFieldValidationAdapter:
    if settings.llm_mode == "mock":
        return DeterministicFieldValidationAdapter()
    if not settings.openai_api_key:
        return UnavailableFieldValidationAdapter("OPENAI_API_KEY is not configured")
    if not settings.openai_model:
        return UnavailableFieldValidationAdapter("OPENAI_MODEL is not configured")
    return LangChainOpenAiFieldValidationAdapter(
        settings.llm_base_url,
        settings.openai_api_key,
        settings.openai_model,
        settings.llm_token_usage_log_enabled,
    )
