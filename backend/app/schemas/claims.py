from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import ClaimStatus, EvidenceCategory


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
