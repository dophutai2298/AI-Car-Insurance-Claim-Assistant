from enum import Enum

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    ADJUSTER = "ADJUSTER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole, native_enum=False))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ClaimStatus(str, Enum):
    DRAFT = "DRAFT"
    ANALYZING = "ANALYZING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    AI_APPROVED = "AI_APPROVED"
    AI_REJECTED = "AI_REJECTED"
    FAILED = "FAILED"


class EvidenceCategory(str, Enum):
    VEHICLE_DAMAGE_IMAGE = "VEHICLE_DAMAGE_IMAGE"
    ID_CARD = "ID_CARD"
    INSURANCE_POLICY = "INSURANCE_POLICY"
    VEHICLE_REGISTRATION = "VEHICLE_REGISTRATION"
    DRIVER_LICENSE = "DRIVER_LICENSE"
    OTHER_DOCUMENT = "OTHER_DOCUMENT"


class DamageAssessment(str, Enum):
    NO_DAMAGE = "NO_DAMAGE"
    REPAIR_LIKELY = "REPAIR_LIKELY"
    REPLACEMENT_LIKELY = "REPLACEMENT_LIKELY"
    MANUAL_INSPECTION_REQUIRED = "MANUAL_INSPECTION_REQUIRED"


class DamageDetectionStatus(str, Enum):
    DETECTED = "DETECTED"
    NO_SIGNIFICANT_DAMAGE = "NO_SIGNIFICANT_DAMAGE"


class ReferencePriceStatus(str, Enum):
    FOUND = "FOUND"
    UNAVAILABLE = "UNAVAILABLE"


class ReferencePriceLookupStatus(str, Enum):
    FOUND = "FOUND"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_REQUESTED = "NOT_REQUESTED"


class CopilotConclusionStatus(str, Enum):
    GENERATED = "GENERATED"
    FALLBACK = "FALLBACK"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"


class CopilotConclusionReviewStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CopilotConclusionRejectionCategory(str, Enum):
    DOCUMENT_INFORMATION_INCOMPLETE = "DOCUMENT_INFORMATION_INCOMPLETE"
    DOCUMENT_INFORMATION_INCORRECT = "DOCUMENT_INFORMATION_INCORRECT"
    DAMAGE_ASSESSMENT_ISSUE = "DAMAGE_ASSESSMENT_ISSUE"
    DAMAGE_EVIDENCE_ISSUE = "DAMAGE_EVIDENCE_ISSUE"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    INCORRECT_AI_CONCLUSION = "INCORRECT_AI_CONCLUSION"
    OTHER = "OTHER"


class AssessmentRuleConfiguration(Base):
    __tablename__ = "assessment_rule_configurations"
    __table_args__ = (CheckConstraint("id = 1", name="assessment_rule_configurations_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    confidence_threshold: Mapped[float] = mapped_column(Float)
    repair_max_percentage: Mapped[float] = mapped_column(Float)
    replacement_min_percentage: Mapped[float] = mapped_column(Float)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class AssessmentRuleChange(Base):
    __tablename__ = "assessment_rule_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    changed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    old_confidence_threshold: Mapped[float] = mapped_column(Float)
    old_repair_max_percentage: Mapped[float] = mapped_column(Float)
    old_replacement_min_percentage: Mapped[float] = mapped_column(Float)
    new_confidence_threshold: Mapped[float] = mapped_column(Float)
    new_repair_max_percentage: Mapped[float] = mapped_column(Float)
    new_replacement_min_percentage: Mapped[float] = mapped_column(Float)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_number: Mapped[str | None] = mapped_column(String(24), unique=True, index=True, nullable=True)
    claimant_name: Mapped[str] = mapped_column(String(120))
    vehicle_make: Mapped[str] = mapped_column(String(80))
    vehicle_model: Mapped[str] = mapped_column(String(80))
    vehicle_year: Mapped[int] = mapped_column(Integer)
    license_plate: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[ClaimStatus] = mapped_column(
        SqlEnum(ClaimStatus, native_enum=False), default=ClaimStatus.DRAFT
    )
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), index=True)
    category: Mapped[EvidenceCategory] = mapped_column(
        SqlEnum(EvidenceCategory, native_enum=False)
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class DamageAnalysis(Base):
    __tablename__ = "damage_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_number: Mapped[str | None] = mapped_column(String(24), unique=True, index=True, nullable=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), index=True)
    assessment: Mapped[DamageAssessment] = mapped_column(SqlEnum(DamageAssessment, native_enum=False))
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class DamageDetection(Base):
    __tablename__ = "damage_detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("damage_analyses.id"), index=True)
    source_evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"))
    annotated_evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"))
    vehicle_part: Mapped[str | None] = mapped_column(String(80), nullable=True)
    damage_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    damage_percentage: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[DamageDetectionStatus] = mapped_column(
        SqlEnum(DamageDetectionStatus, native_enum=False)
    )


class DamageAnalysisRuleSnapshot(Base):
    __tablename__ = "damage_analysis_rule_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("damage_analyses.id"), unique=True, index=True)
    confidence_threshold: Mapped[float] = mapped_column(Float)
    repair_max_percentage: Mapped[float] = mapped_column(Float)
    replacement_min_percentage: Mapped[float] = mapped_column(Float)


class ReferencePartPrice(Base):
    __tablename__ = "reference_part_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("damage_analyses.id"), index=True)
    part_identity: Mapped[str] = mapped_column(String(80))
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price_type: Mapped[str] = mapped_column(String(64))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReferencePriceStatus] = mapped_column(
        SqlEnum(ReferencePriceStatus, native_enum=False)
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class CopilotConclusion(Base):
    __tablename__ = "copilot_conclusions"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("damage_analyses.id"), unique=True, index=True)
    status: Mapped[CopilotConclusionStatus] = mapped_column(
        SqlEnum(CopilotConclusionStatus, native_enum=False)
    )
    recommendation: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text)
    fallback_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class CopilotConclusionReview(Base):
    __tablename__ = "copilot_conclusion_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), index=True)
    conclusion_id: Mapped[int] = mapped_column(
        ForeignKey("copilot_conclusions.id"), unique=True, index=True
    )
    status: Mapped[CopilotConclusionReviewStatus] = mapped_column(
        SqlEnum(CopilotConclusionReviewStatus, native_enum=False)
    )
    reason_category: Mapped[CopilotConclusionRejectionCategory | None] = mapped_column(
        SqlEnum(CopilotConclusionRejectionCategory, native_enum=False), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
