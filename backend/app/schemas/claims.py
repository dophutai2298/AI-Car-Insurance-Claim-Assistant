from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    ClaimStatus,
    DamageAssessment,
    DamageDetectionStatus,
    EvidenceCategory,
    CopilotConclusionStatus,
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


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claimant_name: str
    vehicle: VehicleMetadata
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime
    evidence: list["EvidenceResponse"] = Field(default_factory=list)
    latest_damage_analysis: "DamageAnalysisResponse | None" = None


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
    status: CopilotConclusionStatus
    recommendation: str
    summary: str
    fallback_summary: str | None
    failure_reason: str | None
    provider_model: str | None
    findings: list[CopilotFindingResponse]
    warnings: list[str]
    reference_prices: list[ReferencePartPriceResponse]
