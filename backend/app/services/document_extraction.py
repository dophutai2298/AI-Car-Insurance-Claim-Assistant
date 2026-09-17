from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import re
from time import perf_counter
from typing import Protocol

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.config import Settings
from app.models import AnalysisResultStatus, EvidenceCategory


PROMPT_VERSION = "document-extraction-v1"
SCHEMA_VERSION = "document-extraction-schema-v1"
PROMPT_RESOURCE = Path(__file__).resolve().parents[1] / "prompts" / "systemprompt_document.md"
SUPPORTED_EXTRACTION_CATEGORIES = {
    EvidenceCategory.ID_CARD,
    EvidenceCategory.INSURANCE_POLICY,
    EvidenceCategory.VEHICLE_REGISTRATION,
    EvidenceCategory.DRIVER_LICENSE,
}
logger = logging.getLogger(__name__)


def _normalize_document_date(value: object) -> object:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        return None
    for date_format in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(normalized, date_format).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return None


class NormalizedExtractionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before", check_fields=False)
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class IdentityCardExtraction(NormalizedExtractionModel):
    full_name: str | None = None
    identity_number: str | None = None
    date_of_birth: str | None = None
    place_of_origin: str | None = None
    expiry_date: str | None = None

    @field_validator("date_of_birth", "expiry_date", mode="before")
    @classmethod
    def normalize_date(cls, value: object) -> object:
        return _normalize_document_date(value)


class InsurancePolicyExtraction(NormalizedExtractionModel):
    vehicle_owner: str | None = None
    vehicle_brand: str | None = None


class VehicleRegistrationExtraction(NormalizedExtractionModel):
    vehicle_owner: str | None = None
    vehicle_brand: str | None = None
    vehicle_type: str | None = None
    license_plate: str | None = None


class DriverLicenseExtraction(NormalizedExtractionModel):
    license_number: str | None = None
    full_name: str | None = None
    expiry_date: str | None = None

    @field_validator("expiry_date", mode="before")
    @classmethod
    def normalize_date(cls, value: object) -> object:
        return _normalize_document_date(value)


@dataclass(frozen=True)
class DocumentExtractionDefinition:
    category: EvidenceCategory
    system_prompt: str
    output_schema: type[BaseModel]
    prompt_version: str = PROMPT_VERSION
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class ExtractedFieldValue:
    field_key: str
    value: str | None


@dataclass(frozen=True)
class DocumentExtractionOutcome:
    category: EvidenceCategory
    status: AnalysisResultStatus
    fields: list[ExtractedFieldValue]
    prompt_version: str
    schema_version: str
    warning: str | None = None


class DocumentExtractionError(Exception):
    pass


class DocumentPromptResolver:
    _section_number = {
        EvidenceCategory.ID_CARD: 1,
        EvidenceCategory.INSURANCE_POLICY: 2,
        EvidenceCategory.VEHICLE_REGISTRATION: 3,
        EvidenceCategory.DRIVER_LICENSE: 4,
    }

    def __init__(self, resource_path: Path = PROMPT_RESOURCE) -> None:
        self.resource_path = resource_path
        self._sections: dict[int, str] | None = None

    def resolve(self, category: EvidenceCategory) -> str:
        if self._sections is None:
            self._sections = self._load_sections()
        section_number = self._section_number.get(category)
        if section_number is None or section_number not in self._sections:
            raise DocumentExtractionError(f"Document extraction is not supported for {category.value}")
        return self._sections[section_number]

    def _load_sections(self) -> dict[int, str]:
        try:
            content = self.resource_path.read_text(encoding="utf-8")
        except OSError as error:
            raise DocumentExtractionError("Document extraction prompt resource is unavailable") from error
        matches = list(re.finditer(r"^##\s+(\d+)\.\s+", content, flags=re.MULTILINE))
        sections: dict[int, str] = {}
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            sections[int(match.group(1))] = content[match.start() : end].strip()
        return sections


class DocumentExtractionAdapter(Protocol):
    def extract(
        self,
        definition: DocumentExtractionDefinition,
        raw_ocr_text: str,
    ) -> BaseModel: ...


def _labeled_value(raw_ocr_text: str, aliases: tuple[str, ...]) -> str | None:
    for line in raw_ocr_text.splitlines():
        for alias in aliases:
            match = re.match(rf"\s*{re.escape(alias)}\s*[:\-]\s*(.+?)\s*$", line, re.IGNORECASE)
            if match:
                return match.group(1).strip() or None
    return None


class DeterministicDocumentExtractionAdapter:
    def extract(
        self,
        definition: DocumentExtractionDefinition,
        raw_ocr_text: str,
    ) -> BaseModel:
        if definition.category is EvidenceCategory.ID_CARD:
            return IdentityCardExtraction(
                full_name=_labeled_value(raw_ocr_text, ("full name", "họ và tên", "ho va ten")),
                identity_number=_labeled_value(
                    raw_ocr_text, ("identity number", "số cccd", "so cccd", "số cmnd", "so cmnd")
                ),
                date_of_birth=_labeled_value(
                    raw_ocr_text, ("date of birth", "ngày sinh", "ngay sinh")
                ),
                place_of_origin=_labeled_value(
                    raw_ocr_text, ("place of origin", "quê quán", "que quan")
                ),
                expiry_date=_labeled_value(
                    raw_ocr_text, ("date of expiry", "expiry date", "có giá trị đến", "co gia tri den")
                ),
            )
        if definition.category is EvidenceCategory.INSURANCE_POLICY:
            return InsurancePolicyExtraction(
                vehicle_owner=_labeled_value(
                    raw_ocr_text, ("vehicle owner", "policy vehicle owner", "chủ xe", "chu xe")
                ),
                vehicle_brand=_labeled_value(
                    raw_ocr_text, ("vehicle brand", "brand", "make", "hiệu xe", "hieu xe")
                ),
            )
        if definition.category is EvidenceCategory.VEHICLE_REGISTRATION:
            return VehicleRegistrationExtraction(
                vehicle_owner=_labeled_value(
                    raw_ocr_text, ("vehicle owner", "owner name", "tên chủ xe", "ten chu xe")
                ),
                vehicle_brand=_labeled_value(
                    raw_ocr_text,
                    ("vehicle brand", "vehicle make", "brand", "make", "nhãn hiệu", "nhan hieu"),
                ),
                vehicle_type=_labeled_value(
                    raw_ocr_text, ("vehicle type", "type", "loại xe", "loai xe")
                ),
                license_plate=_labeled_value(
                    raw_ocr_text,
                    ("license plate", "number plate", "biển số đăng ký", "bien so dang ky"),
                ),
            )
        if definition.category is EvidenceCategory.DRIVER_LICENSE:
            return DriverLicenseExtraction(
                license_number=_labeled_value(
                    raw_ocr_text,
                    ("license number", "số giấy phép lái xe", "so giay phep lai xe", "số gplx", "so gplx"),
                ),
                full_name=_labeled_value(raw_ocr_text, ("full name", "họ và tên", "ho va ten")),
                expiry_date=_labeled_value(
                    raw_ocr_text,
                    ("expiry date", "expires", "có giá trị đến", "co gia tri den"),
                ),
            )
        raise DocumentExtractionError(
            f"Document extraction is not supported for {definition.category.value}"
        )


class UnavailableDocumentExtractionAdapter:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def extract(
        self,
        definition: DocumentExtractionDefinition,
        raw_ocr_text: str,
    ) -> BaseModel:
        raise DocumentExtractionError(self.reason)


class LangChainOpenAiDocumentExtractionAdapter:
    def __init__(
        self,
        base_url: str | None,
        api_key: str,
        model: str,
        request_timeout_seconds: float = 60.0,
        max_retries: int = 0,
    ) -> None:
        from langchain_openai import ChatOpenAI

        options: dict[str, object] = {
            "model": model,
            "api_key": api_key,
            "temperature": 0,
            "timeout": request_timeout_seconds,
            "max_retries": max_retries,
        }
        if base_url:
            options["base_url"] = base_url
        self.model = ChatOpenAI(**options)
        self.model_name = model

    def extract(
        self,
        definition: DocumentExtractionDefinition,
        raw_ocr_text: str,
    ) -> BaseModel:
        started_at = perf_counter()
        try:
            from langchain.messages import HumanMessage, SystemMessage

            structured_model = self.model.with_structured_output(
                definition.output_schema, method="json_schema"
            )
            response = structured_model.invoke(
                [
                    SystemMessage(content=definition.system_prompt),
                    HumanMessage(
                        content=json.dumps(
                            {"raw_ocr_text": raw_ocr_text},
                            ensure_ascii=False,
                        )
                    ),
                ]
            )
            logger.info(
                "Document extraction completed for %s using %s in %.2fs",
                definition.category.value,
                self.model_name,
                perf_counter() - started_at,
            )
            return definition.output_schema.model_validate(response)
        except Exception as error:
            logger.warning(
                "OpenAI document extraction failed for %s using %s after %.2fs (%s)",
                definition.category.value,
                self.model_name,
                perf_counter() - started_at,
                type(error).__name__,
            )
            raise DocumentExtractionError(
                f"Document extraction unavailable ({type(error).__name__})."
            ) from error


class DocumentExtractionService:
    _schema_by_category: dict[EvidenceCategory, type[BaseModel]] = {
        EvidenceCategory.ID_CARD: IdentityCardExtraction,
        EvidenceCategory.INSURANCE_POLICY: InsurancePolicyExtraction,
        EvidenceCategory.VEHICLE_REGISTRATION: VehicleRegistrationExtraction,
        EvidenceCategory.DRIVER_LICENSE: DriverLicenseExtraction,
    }

    def __init__(
        self,
        adapter: DocumentExtractionAdapter,
        prompt_resolver: DocumentPromptResolver | None = None,
    ) -> None:
        self.adapter = adapter
        self.prompt_resolver = prompt_resolver or DocumentPromptResolver()

    def supports(self, category: EvidenceCategory) -> bool:
        return category in SUPPORTED_EXTRACTION_CATEGORIES

    def extract(
        self,
        category: EvidenceCategory,
        raw_ocr_text: str,
    ) -> DocumentExtractionOutcome:
        schema = self._schema_by_category.get(category)
        if schema is None:
            raise DocumentExtractionError(f"Document extraction is not supported for {category.value}")
        try:
            definition = DocumentExtractionDefinition(
                category=category,
                system_prompt=self.prompt_resolver.resolve(category),
                output_schema=schema,
            )
            extracted = self.adapter.extract(definition, raw_ocr_text)
            validated = schema.model_validate(extracted)
            fields = [
                ExtractedFieldValue(field_key=field_key, value=value)
                for field_key, value in validated.model_dump().items()
            ]
            return DocumentExtractionOutcome(
                category=category,
                status=AnalysisResultStatus.COMPLETED,
                fields=fields,
                prompt_version=definition.prompt_version,
                schema_version=definition.schema_version,
            )
        except DocumentExtractionError as error:
            return DocumentExtractionOutcome(
                category=category,
                status=AnalysisResultStatus.FAILED,
                fields=[],
                prompt_version=PROMPT_VERSION,
                schema_version=SCHEMA_VERSION,
                warning=str(error),
            )
        except Exception as error:
            return DocumentExtractionOutcome(
                category=category,
                status=AnalysisResultStatus.FAILED,
                fields=[],
                prompt_version=PROMPT_VERSION,
                schema_version=SCHEMA_VERSION,
                warning=f"Structured document extraction failed ({type(error).__name__}).",
            )


def get_document_extraction_adapter(settings: Settings) -> DocumentExtractionAdapter:
    if settings.llm_mode == "mock":
        return DeterministicDocumentExtractionAdapter()
    if not settings.openai_api_key:
        return UnavailableDocumentExtractionAdapter("OPENAI_API_KEY is not configured")
    if not settings.openai_model:
        return UnavailableDocumentExtractionAdapter("OPENAI_MODEL is not configured")
    return LangChainOpenAiDocumentExtractionAdapter(
        settings.llm_base_url,
        settings.openai_api_key,
        settings.openai_model,
        settings.llm_request_timeout_seconds,
        settings.llm_max_retries,
    )
