from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import (
    AnalysisResultStatus,
    AnalysisRunStatus,
    ClaimStatus,
    ConsistencyStatus,
    DamageAssessment,
    DamageDetectionStatus,
    EvidenceCategory,
    DocumentFieldStatus,
    FieldValidationStatus,
    CopilotConclusionStatus,
    CopilotConclusionRejectionCategory,
    CopilotConclusionReviewStatus,
    ReferencePriceLookupStatus,
    ReferencePriceStatus,
)
from app.schemas.admin import AssessmentRuleValuesSchema


class VehicleMetadata(BaseModel):
    make: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    year: int = Field(ge=1900, le=2100)
    license_plate: str | None = Field(default=None, max_length=32)
    vin: str | None = Field(default=None, max_length=32)


class ClaimCreateRequest(BaseModel):
    claimant_name: str = Field(min_length=1, max_length=120)
    vehicle: VehicleMetadata
    incident: "IncidentInformation | None" = None


class IncidentInformation(BaseModel):
    occurred_at: datetime
    location: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=4000)


class ClaimInformationUpdateRequest(BaseModel):
    claimant_name: str = Field(min_length=1, max_length=120)
    vehicle: VehicleMetadata
    incident: IncidentInformation


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claimant_name: str
    vehicle: VehicleMetadata
    incident: IncidentInformation | None = None
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime
    evidence: list["EvidenceResponse"] = Field(default_factory=list)
    latest_damage_analysis: "DamageAnalysisResponse | None" = None
    latest_analysis_run: "WorkflowAnalysisRunResponse | None" = None
    copilot_review_history: list["CopilotConclusionReviewResponse"] = Field(default_factory=list)


class ClaimListItem(BaseModel):
    id: str
    claimant_name: str
    vehicle_summary: str
    status: ClaimStatus
    updated_at: datetime


class ClaimStatusUpdateRequest(BaseModel):
    status: ClaimStatus


class EvidenceResponse(BaseModel):
    id: int
    category: EvidenceCategory
    original_filename: str
    content_type: str | None
    file_size: int
    uploaded_at: datetime
    content_url: str
    group_id: int | None = None
    group_label: str | None = None
    analysis_required: bool = False


class DamageDetectionResponse(BaseModel):
    vehicle_part: str | None
    damage_type: str | None
    damage_percentage: float
    confidence: float
    status: DamageDetectionStatus
    annotated_evidence: EvidenceResponse


class DamageTypeResponse(BaseModel):
    type: str
    percent: float


class DamagePartResponse(BaseModel):
    part: str
    main_damage: str
    damage_percent: float
    damage_types: list[DamageTypeResponse] = Field(default_factory=list)


class CarDamageRecordResponse(BaseModel):
    source_evidence_ids: list[int] = Field(default_factory=list)
    annotated_evidence_ids: list[int] = Field(default_factory=list)
    parts: list[DamagePartResponse] = Field(default_factory=list)


class DamageModelOutputResponse(BaseModel):
    adapter_name: str
    part_identities: list[str] = Field(default_factory=list)
    record: CarDamageRecordResponse
    warnings: list[str] = Field(default_factory=list)


class DamageAnalysisResponse(BaseModel):
    id: str
    assessment: DamageAssessment
    warning: str | None
    detections: list[DamageDetectionResponse]
    model_output: DamageModelOutputResponse | None = None
    rules: AssessmentRuleValuesSchema | None = None
    reference_price_status: ReferencePriceLookupStatus
    reference_prices: list["ReferencePartPriceResponse"] = Field(default_factory=list)
    copilot_conclusion: "CopilotConclusionResponse | None" = None
    created_at: datetime


class DocumentAnalysisFieldResponse(BaseModel):
    id: int
    key: str
    label: str
    original_ai_value: str
    reviewed_value: str
    confidence: float
    status: DocumentFieldStatus


class DocumentAnalysisFieldUpdateRequest(BaseModel):
    reviewed_value: str = Field(min_length=1, max_length=2000)


class DocumentFieldValidationUpdateRequest(BaseModel):
    reviewed_value: str = Field(min_length=1, max_length=2000)


class DocumentExtractedFieldUpdateRequest(BaseModel):
    confirmed_value: str | None = Field(default=None, max_length=2000)


class DocumentExtractedFieldBatchItem(BaseModel):
    id: int = Field(gt=0)
    confirmed_value: str | None = Field(default=None, max_length=2000)


class DocumentExtractedFieldsBatchUpdateRequest(BaseModel):
    fields: list[DocumentExtractedFieldBatchItem] = Field(min_length=1)

    @model_validator(mode="after")
    def field_ids_must_be_unique(self):
        ids = [field.id for field in self.fields]
        if len(ids) != len(set(ids)):
            raise ValueError("Document extracted field ids must be unique")
        return self


class DocumentFieldComparisonResponse(BaseModel):
    claim_value: str | None
    document_value: str | None
    status: ConsistencyStatus
    explanation: str


class DocumentAnalysisResponse(BaseModel):
    id: int
    document_type: EvidenceCategory
    status: AnalysisResultStatus
    fields: list[DocumentAnalysisFieldResponse]
    warnings: list[str]


class DocumentOcrResultResponse(BaseModel):
    id: int
    source_evidence_id: int
    document_type: EvidenceCategory
    original_filename: str
    content_type: str | None
    status: AnalysisResultStatus
    raw_text: str | None
    adapter_name: str | None
    adapter_metadata: dict[str, object]
    warning: str | None
    created_at: datetime
    processed_at: datetime | None
    reused: bool = False
    extraction: "DocumentExtractionResultResponse | None" = None
    field_validations: list["DocumentFieldValidationResponse"] = Field(default_factory=list)


class DocumentExtractedFieldResponse(BaseModel):
    id: int
    analysis_run_id: int
    extraction_result_id: int
    source_evidence_id: int
    field_key: str
    ai_extracted_value: str | None
    confirmed_value: str | None
    prompt_version: str
    schema_version: str
    created_at: datetime
    updated_at: datetime
    comparison: DocumentFieldComparisonResponse | None = None


class DocumentExtractionResultResponse(BaseModel):
    id: int
    analysis_run_id: int
    document_ocr_result_id: int
    source_evidence_id: int
    document_type: EvidenceCategory
    status: AnalysisResultStatus
    prompt_version: str
    schema_version: str
    warning: str | None
    created_at: datetime
    processed_at: datetime | None
    reused: bool = False
    fields: list[DocumentExtractedFieldResponse] = Field(default_factory=list)


class DocumentFieldValidationResponse(BaseModel):
    id: int
    analysis_run_id: int
    document_ocr_result_id: int
    source_evidence_id: int
    field_key: str
    prompt_version: str
    ocr_value: str | None
    normalized_value: str | None
    status: FieldValidationStatus
    confidence: float
    summary: str
    warnings: list[str]


class ClaimConsistencyCheckResponse(BaseModel):
    id: int
    field_validation_id: int
    source_evidence_id: int
    field_key: str
    claim_value: str
    document_value: str
    status: ConsistencyStatus
    explanation: str


class AnalysisBlockedReasonResponse(BaseModel):
    code: str
    message: str
    category: EvidenceCategory | None = None
    field_id: int | None = None
    field_key: str | None = None


class AnalysisReadinessResponse(BaseModel):
    status: Literal["NOT_SAVED", "BLOCKED", "READY", "STALE"]
    blocked_reasons: list[AnalysisBlockedReasonResponse] = Field(default_factory=list)


class ConfirmedAnalysisSnapshotResponse(BaseModel):
    status: Literal["READY", "STALE"]
    documents: list[dict[str, object]] = Field(default_factory=list)
    damage: dict[str, object]
    warnings: list[str] = Field(default_factory=list)
    evidence_references: list[dict[str, object]] = Field(default_factory=list)
    saved_at: datetime


class WorkflowAnalysisRunResponse(BaseModel):
    id: int
    status: AnalysisRunStatus
    damage_status: AnalysisResultStatus
    damage_analysis: DamageAnalysisResponse | None = None
    document_analyses: list[DocumentAnalysisResponse] = Field(default_factory=list)
    document_ocr_results: list[DocumentOcrResultResponse] = Field(default_factory=list)
    consistency_checks: list[ClaimConsistencyCheckResponse] = Field(default_factory=list)
    analysis_readiness: AnalysisReadinessResponse
    analysis_snapshot: ConfirmedAnalysisSnapshotResponse | None = None
    failure_reason: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    inputs_changed: bool = False


class ReferencePartPriceResponse(BaseModel):
    part_identity: str
    amount: float | None
    currency: str | None
    source_name: str | None
    source_url: str | None
    price_type: str
    retrieved_at: datetime
    status: ReferencePriceStatus
    failure_reason: str | None


class CopilotFindingResponse(BaseModel):
    vehicle_part: str | None
    damage_type: str | None
    damage_percentage: float
    confidence: float
    annotated_evidence: EvidenceResponse


class AiReviewStructuredResponse(BaseModel):
    summary: str
    assessment_interpretation: str
    damaged_parts_summary: str
    document_consistency_summary: str
    warnings: list[str] = Field(default_factory=list)
    recommended_next_step: str
    human_review_required: bool


class CopilotConclusionResponse(BaseModel):
    id: int
    status: CopilotConclusionStatus
    recommendation: str
    summary: str
    fallback_summary: str | None
    failure_reason: str | None
    provider_model: str | None
    findings: list[CopilotFindingResponse]
    warnings: list[str]
    reference_prices: list[ReferencePartPriceResponse]
    review_history: list["CopilotConclusionReviewResponse"] = Field(default_factory=list)
    validity_percentage: int | None = Field(default=None, ge=0, le=100)
    review_status: str | None = None
    evidence_references: list["EvidenceReferenceResponse"] = Field(default_factory=list)
    structured_review: AiReviewStructuredResponse | None = None
    prompt_version: str | None = None
    schema_version: str | None = None


class EvidenceReferenceResponse(BaseModel):
    id: int
    category: EvidenceCategory
    original_filename: str


class CopilotConclusionReviewRequest(BaseModel):
    status: CopilotConclusionReviewStatus
    reason_category: CopilotConclusionRejectionCategory | None = None
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_rejection_feedback(self) -> "CopilotConclusionReviewRequest":
        if not self.comment or not self.comment.strip():
            raise ValueError("A review note is required")
        if self.status is CopilotConclusionReviewStatus.REJECTED:
            if self.reason_category is None:
                raise ValueError("A rejection reason category is required")
        elif self.reason_category is not None:
            raise ValueError("Approval does not accept a rejection category")
        return self


class CopilotConclusionReviewRevertRequest(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class CopilotConclusionReviewResponse(BaseModel):
    claim_id: str
    conclusion_id: int
    status: CopilotConclusionReviewStatus
    reason_category: CopilotConclusionRejectionCategory | None
    comment: str | None
    reviewer: str
    reviewed_at: datetime
    reverted_at: datetime | None = None
    reverted_by: str | None = None
    revert_note: str | None = None
