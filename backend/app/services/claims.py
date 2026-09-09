from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import (
    Claim,
    ClaimStatus,
    DamageAnalysis,
    Evidence,
    EvidenceCategory,
    ReferencePartPrice,
    ReferencePriceLookupStatus,
    ReferencePriceStatus,
    User,
)
from app.repositories.claims import ClaimRepository
from app.repositories.damage_analyses import DamageAnalysisRepository
from app.repositories.evidence import EvidenceRepository
from app.schemas.claims import (
    ClaimCreateRequest,
    DamageAnalysisResponse,
    DamageDetectionResponse,
    ClaimListItem,
    ClaimResponse,
    EvidenceResponse,
    ReferencePartPriceResponse,
    VehicleMetadata,
)
from app.schemas.admin import AssessmentRuleValuesSchema
from app.services.assessment_rules import AssessmentRuleService
from app.services.evidence_storage import EvidenceStorage, EvidenceStorageError, StoredEvidence
from app.services.damage_assessment import DamageAssessmentService
from app.services.damage_model import DamageModelAdapter
from app.services.part_search import PartSearchService

ALLOWED_LIFECYCLE_TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    ClaimStatus.DRAFT: {ClaimStatus.ANALYZING},
    ClaimStatus.ANALYZING: {ClaimStatus.REVIEW_REQUIRED, ClaimStatus.FAILED},
    ClaimStatus.FAILED: {ClaimStatus.ANALYZING},
}


class EvidencePersistenceError(Exception):
    pass


class ClaimService:
    def __init__(
        self,
        session: Session,
        storage: EvidenceStorage,
        damage_model: DamageModelAdapter,
        assessment: DamageAssessmentService,
        rules: AssessmentRuleService,
        part_search: PartSearchService,
    ):
        self.claims = ClaimRepository(session)
        self.evidence = EvidenceRepository(session)
        self.damage_analyses = DamageAnalysisRepository(session)
        self.storage = storage
        self.damage_model = damage_model
        self.assessment = assessment
        self.rules = rules
        self.part_search = part_search

    def create_claim(self, data: ClaimCreateRequest, created_by: User) -> ClaimResponse:
        return self._to_response(self.claims.create(data, created_by.id))

    def list_claims(self) -> list[ClaimListItem]:
        return [
            ClaimListItem(
                id=claim.claim_number,
                claimant_name=claim.claimant_name,
                vehicle_summary=f"{claim.vehicle_year} {claim.vehicle_make} {claim.vehicle_model}",
                status=claim.status,
                updated_at=claim.updated_at,
            )
            for claim in self.claims.list_all()
            if claim.claim_number
        ]

    def get_claim(self, claim_number: str) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        return self._to_response(claim) if claim else None

    def transition_claim(self, claim_number: str, next_status: ClaimStatus) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        if next_status not in ALLOWED_LIFECYCLE_TRANSITIONS.get(claim.status, set()):
            raise ValueError("Invalid claim lifecycle transition")
        return self._to_response(self.claims.update_status(claim, next_status))

    def upload_evidence(
        self,
        claim_number: str,
        categories: list[EvidenceCategory],
        files: list[UploadFile],
    ) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        if len(files) != len(categories):
            raise ValueError("Each uploaded file must have exactly one evidence category")

        stored_uploads = self.storage.save_all(claim_number, files)
        uploads = list(zip(categories, stored_uploads, strict=True))
        try:
            self.evidence.create_many(claim, uploads)
        except SQLAlchemyError as error:
            self.claims.session.rollback()
            self.storage.delete_stored(stored_uploads)
            raise EvidencePersistenceError("Unable to persist uploaded evidence") from error

        return self._to_response(claim)

    def evidence_content_path(self, claim_number: str, evidence_id: int) -> tuple[Evidence, Path] | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        evidence = self.evidence.find_for_claim(claim.id, evidence_id)
        if evidence is None:
            return None
        path = self.storage.resolve_path(evidence.stored_path)
        return (evidence, path) if path.is_file() else None

    def run_damage_analysis(
        self, claim_number: str, force_reference_price_lookup: bool = False
    ) -> DamageAnalysisResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        images = [
            item
            for item in self.evidence.list_for_claim(claim.id)
            if item.category is EvidenceCategory.VEHICLE_DAMAGE_IMAGE
        ]
        if not images:
            raise ValueError("Upload at least one vehicle damage image before running analysis")
        detections = self.damage_model.analyze(images)
        rules = self.rules.active_values()
        assessment = self.assessment.assess(detections, rules)
        reference_prices = self.part_search.lookup_for_assessment(
            assessment.assessment,
            detections,
            claim.vehicle_make,
            claim.vehicle_model,
            claim.vehicle_year,
            force_reference_price_lookup,
        )
        analysis = self.damage_analyses.create(
            claim,
            assessment,
            detections,
            rules,
            reference_prices,
        )
        return self._to_damage_analysis_response(claim.claim_number, analysis)

    def _to_response(self, claim: Claim) -> ClaimResponse:
        if claim.claim_number is None:
            raise ValueError("Claim number must be assigned before serialization")

        return ClaimResponse(
            id=claim.claim_number,
            claimant_name=claim.claimant_name,
            vehicle=VehicleMetadata(
                make=claim.vehicle_make,
                model=claim.vehicle_model,
                year=claim.vehicle_year,
                license_plate=claim.license_plate,
                vin=claim.vin,
            ),
            status=claim.status,
            created_at=claim.created_at,
            updated_at=claim.updated_at,
            evidence=[
                self._to_evidence_response(claim.claim_number, item)
                for item in self.evidence.list_for_claim(claim.id)
            ],
            latest_damage_analysis=self._latest_damage_analysis_response(claim.claim_number, claim.id),
        )

    def _latest_damage_analysis_response(self, claim_number: str, claim_id: int) -> DamageAnalysisResponse | None:
        analysis = self.damage_analyses.latest_for_claim(claim_id)
        return self._to_damage_analysis_response(claim_number, analysis) if analysis else None

    def _to_damage_analysis_response(self, claim_number: str, analysis: DamageAnalysis) -> DamageAnalysisResponse:
        if analysis.analysis_number is None:
            raise ValueError("Damage analysis number must be assigned before serialization")
        evidence_by_id = {item.id: item for item in self.evidence.list_for_claim(analysis.claim_id)}
        detections = []
        for detection in self.damage_analyses.list_detections(analysis.id):
            annotated_evidence = evidence_by_id.get(detection.annotated_evidence_id)
            if annotated_evidence is None:
                raise ValueError("Annotated evidence must be available before serialization")
            detections.append(
                DamageDetectionResponse(
                    vehicle_part=detection.vehicle_part,
                    damage_type=detection.damage_type,
                    damage_percentage=detection.damage_percentage,
                    confidence=detection.confidence,
                    status=detection.status,
                    annotated_evidence=self._to_evidence_response(claim_number, annotated_evidence),
                )
            )
        reference_prices = self.damage_analyses.reference_prices(analysis.id)
        return DamageAnalysisResponse(
            id=analysis.analysis_number,
            assessment=analysis.assessment,
            warning=analysis.warning,
            detections=detections,
            rules=self._rules_for_analysis(analysis.id),
            reference_price_status=self._reference_price_status(reference_prices),
            reference_prices=[self._to_reference_price_response(price) for price in reference_prices],
            created_at=analysis.created_at,
        )

    @staticmethod
    def _reference_price_status(prices: list[ReferencePartPrice]) -> ReferencePriceLookupStatus:
        if not prices:
            return ReferencePriceLookupStatus.NOT_REQUESTED
        return (
            ReferencePriceLookupStatus.FOUND
            if all(price.status is ReferencePriceStatus.FOUND for price in prices)
            else ReferencePriceLookupStatus.UNAVAILABLE
        )

    @staticmethod
    def _to_reference_price_response(price: ReferencePartPrice) -> ReferencePartPriceResponse:
        return ReferencePartPriceResponse(
            part_identity=price.part_identity,
            amount=price.amount,
            currency=price.currency,
            source_name=price.source_name,
            source_url=price.source_url,
            price_type=price.price_type,
            retrieved_at=price.retrieved_at,
            status=price.status,
            failure_reason=price.failure_reason,
        )

    def _rules_for_analysis(self, analysis_id: int) -> AssessmentRuleValuesSchema | None:
        snapshot = self.damage_analyses.rule_snapshot(analysis_id)
        if snapshot is None:
            return None
        return AssessmentRuleValuesSchema(
            confidence_threshold=snapshot.confidence_threshold,
            repair_max_percentage=snapshot.repair_max_percentage,
            replacement_min_percentage=snapshot.replacement_min_percentage,
        )

    @staticmethod
    def _to_evidence_response(claim_number: str, evidence: Evidence) -> EvidenceResponse:
        return EvidenceResponse(
            id=evidence.id,
            category=evidence.category,
            original_filename=evidence.original_filename,
            content_type=evidence.content_type,
            file_size=evidence.file_size,
            uploaded_at=evidence.uploaded_at,
            content_url=f"/api/claims/{claim_number}/evidence/{evidence.id}/content",
        )
