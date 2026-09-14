from dataclasses import dataclass
from typing import Protocol

from app.models import DocumentFieldStatus, Evidence, EvidenceCategory


@dataclass(frozen=True)
class ExtractedDocumentField:
    key: str
    label: str
    value: str
    confidence: float
    status: DocumentFieldStatus = DocumentFieldStatus.VALID


@dataclass(frozen=True)
class DocumentAnalysisResult:
    fields: list[ExtractedDocumentField]
    warnings: list[str]


class DocumentAnalysisError(Exception):
    pass


class DocumentAnalysisAdapter(Protocol):
    def analyze(
        self, category: EvidenceCategory, evidence: list[Evidence]
    ) -> DocumentAnalysisResult: ...


class MockDocumentAnalysisAdapter:
    _fixtures: dict[EvidenceCategory, list[ExtractedDocumentField]] = {
        EvidenceCategory.ID_CARD: [
            ExtractedDocumentField("full_name", "Full name", "Nguyen Van A", 0.97),
            ExtractedDocumentField("identity_number", "Identity number", "079203001234", 0.95),
            ExtractedDocumentField("date_of_birth", "Date of birth", "2003-04-18", 0.91),
        ],
        EvidenceCategory.INSURANCE_POLICY: [
            ExtractedDocumentField("policy_number", "Policy number", "POL-VN-2026-00421", 0.96),
            ExtractedDocumentField("insured_name", "Insured name", "Nguyen Van A", 0.93),
            ExtractedDocumentField("coverage_end", "Coverage end", "2027-01-15", 0.89),
        ],
        EvidenceCategory.VEHICLE_REGISTRATION: [
            ExtractedDocumentField("owner_name", "Owner name", "Nguyen Van A", 0.96),
            ExtractedDocumentField("license_plate", "License plate", "51H-123.45", 0.92),
            ExtractedDocumentField("vehicle_make", "Vehicle make", "Toyota", 0.94),
        ],
        EvidenceCategory.DRIVER_LICENSE: [
            ExtractedDocumentField("license_number", "License number", "790123456789", 0.95),
            ExtractedDocumentField("holder_name", "Holder name", "Nguyen Van A", 0.94),
            ExtractedDocumentField("license_class", "License class", "B2", 0.90),
        ],
    }

    def analyze(
        self, category: EvidenceCategory, evidence: list[Evidence]
    ) -> DocumentAnalysisResult:
        if any("analysis-fail" in item.original_filename.lower() for item in evidence):
            raise DocumentAnalysisError("Mock document analysis failed for this evidence group.")
        fields = self._fixtures.get(category)
        if fields is None:
            raise DocumentAnalysisError("Document type is not supported by the mock adapter.")
        return DocumentAnalysisResult(fields=list(fields), warnings=[])
