import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.models import Evidence, EvidenceCategory


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentOcrResult:
    raw_text: str
    adapter_name: str
    metadata: dict[str, object]
    warning: str | None = None


class DocumentOcrError(Exception):
    pass


class DocumentOcrAdapter(Protocol):
    def extract(self, evidence: Evidence, source_path: Path) -> DocumentOcrResult: ...


class MockDocumentOcrAdapter:
    _text_by_category = {
        EvidenceCategory.ID_CARD: (
            "Full name: Nguyen Van A\n"
            "Identity number: 079203001234\n"
            "Date of birth: 18/04/2003\n"
            "Place of origin: Ho Chi Minh City\n"
            "Date of expiry: 18/04/2033"
        ),
        EvidenceCategory.INSURANCE_POLICY: (
            "Vehicle owner: Nguyen Van A\nVehicle brand: Toyota"
        ),
        EvidenceCategory.VEHICLE_REGISTRATION: (
            "Vehicle owner: Nguyen Van A\n"
            "Vehicle make: Toyota\n"
            "Vehicle type: Ô tô con\n"
            "License plate: 51H-123.45"
        ),
        EvidenceCategory.DRIVER_LICENSE: "License number: 079012345678\nLicense class: B2",
    }

    def extract(self, evidence: Evidence, source_path: Path) -> DocumentOcrResult:
        if "ocr-fail" in evidence.original_filename.lower() or "analysis-fail" in evidence.original_filename.lower():
            raise DocumentOcrError("Mock OCR failed for this evidence image.")
        return DocumentOcrResult(
            raw_text=self._text_by_category[evidence.category],
            adapter_name="mock",
            metadata={"mode": "deterministic"},
        )


class DeepDocOcrAdapter:
    def __init__(self) -> None:
        try:
            from deepdoc_vietocr import DocumentReader
        except ImportError as error:
            raise DocumentOcrError("deepdoc_vietocr is not installed.") from error
        self.reader_type = DocumentReader
        self.reader = None

    def extract(self, evidence: Evidence, source_path: Path) -> DocumentOcrResult:
        try:
            if self.reader is None:
                self.reader = self.reader_type()
            result = self.reader.extract(str(source_path))
        except Exception as error:
            logger.exception(
                "DeepDoc OCR provider failed for evidence_id=%s error_type=%s",
                getattr(evidence, "id", None),
                type(error).__name__,
            )
            raise DocumentOcrError("DeepDoc OCR could not process this evidence image.") from error
        raw_text = str(getattr(result, "text", "") or "").strip()
        return DocumentOcrResult(
            raw_text=raw_text,
            adapter_name="deepdoc_vietocr",
            metadata={
                "has_markdown": bool(getattr(result, "markdown", None)),
                "source_format": source_path.suffix.lower(),
            },
            warning="OCR completed without extracted text." if not raw_text else None,
        )


class FallbackDocumentOcrAdapter:
    def __init__(self, primary: DocumentOcrAdapter, fallback: DocumentOcrAdapter) -> None:
        self.primary = primary
        self.fallback = fallback

    def extract(self, evidence: Evidence, source_path: Path) -> DocumentOcrResult:
        try:
            return self.primary.extract(evidence, source_path)
        except DocumentOcrError as error:
            fallback_result = self.fallback.extract(evidence, source_path)
            return DocumentOcrResult(
                raw_text=fallback_result.raw_text,
                adapter_name=fallback_result.adapter_name,
                metadata={**fallback_result.metadata, "fallback_from": "deepdoc_vietocr"},
                warning=f"{error} Using deterministic OCR fallback.",
            )


def get_document_ocr_adapter(mode: str) -> DocumentOcrAdapter:
    mock = MockDocumentOcrAdapter()
    if mode == "mock":
        return mock
    try:
        return FallbackDocumentOcrAdapter(DeepDocOcrAdapter(), mock)
    except DocumentOcrError:
        return mock
