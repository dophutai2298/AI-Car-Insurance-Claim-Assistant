from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import (
    AnalysisResultStatus,
    AnalysisRunStatus,
    ClaimStatus,
    DamageAssessment,
    DamageDetectionStatus,
    EvidenceCategory,
    DocumentFieldStatus,
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


class DamageDetectionResponse(BaseModel):
    vehicle_part: str | None
    damage_type: str | None
    damage_percentage: float
    confidence: float
    status: DamageDetectionStatus
    annotated_evidence: EvidenceResponse


class DamageAnalysisResponse(BaseModel):
    id: str
    assessment: DamageAssessment
    warning: str | None
    detections: list[DamageDetectionResponse]
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


class WorkflowAnalysisRunResponse(BaseModel):
    id: int
    status: AnalysisRunStatus
    damage_status: AnalysisResultStatus
    damage_analysis: DamageAnalysisResponse | None = None
    document_analyses: list[DocumentAnalysisResponse] = Field(default_factory=list)
    document_ocr_results: list[DocumentOcrResultResponse] = Field(default_factory=list)
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
