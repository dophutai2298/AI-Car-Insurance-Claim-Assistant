import json
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import (
    Claim,
    ClaimStatus,
    CopilotConclusionStatus,
    DamageAssessment,
    DamageAnalysis,
    Evidence,
    EvidenceCategory,
    User,
    WorkflowAnalysisRun,
)
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.repositories.claims import ClaimRepository
from app.repositories.claim_incidents import ClaimIncidentRepository
from app.repositories.damage_analyses import DamageAnalysisRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.copilot_conclusions import CopilotConclusionRepository
from app.repositories.copilot_conclusion_reviews import (
    CopilotConclusionReviewRepository,
)
from app.repositories.workflow_ai_reviews import WorkflowAiReviewRepository
from app.schemas.claims import (
    ClaimCreateRequest,
    ClaimInformationUpdateRequest,
    CopilotConclusionReviewRequest,
    CopilotConclusionReviewRevertRequest,
    DamageAnalysisResponse,
    ClaimListItem,
    ClaimResponse,
    DocumentAnalysisFieldUpdateRequest,
    DocumentExtractedFieldsBatchUpdateRequest,
    DocumentExtractedFieldUpdateRequest,
    DocumentFieldValidationUpdateRequest,
    WorkflowAnalysisRunResponse,
    AnalysisBlockedReasonResponse,
)
from app.services.assessment_rules import AssessmentRuleService
from app.services.analysis_errors import AnalysisConfirmationBlockedError
from app.services.claim_errors import ClaimConflictError, ClaimResourceNotFoundError, ClaimValidationError
from app.services.analysis_snapshots import AnalysisSnapshotOperations
from app.services.claim_reviews import ClaimReviewOperations
from app.services.claim_responses import ClaimResponseAssembler
from app.services.workflow_analysis import WorkflowAnalysisOperations
from app.services.evidence_storage import EvidenceStorage
from app.services.damage_assessment import DamageAssessmentService
from app.services.damage_model import DamageModelAdapter, DamageModelDetection
from app.services.part_search import PartSearchService, ReferencePartPriceResult
from app.services.llm_copilot import (
    AiReviewClaimFacts,
    AiReviewContext,
    AiReviewDamage,
    AiReviewDamageFinding,
    AiReviewReferencePrice,
    AiReviewVehicleFacts,
    CopilotInput,
    LlmCopilotService,
)
from app.services.vehicle_manufacturers import VehicleManufacturerService
from app.services.document_analysis import DocumentAnalysisAdapter
from app.services.document_ocr import DocumentOcrAdapter
from app.services.document_consistency import (
    ClaimConsistencyService,
    ClaimFacts,
)
from app.services.document_extraction import DocumentExtractionService
from app.services.document_pipeline import DocumentAnalysisPipeline
from app.services.document_field_validation import (
    DocumentFieldValidationService,
    ValidatedDocumentField,
)

ALLOWED_LIFECYCLE_TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    ClaimStatus.DRAFT: {ClaimStatus.ANALYZING},
    ClaimStatus.ANALYZING: {ClaimStatus.REVIEW_REQUIRED, ClaimStatus.FAILED},
    ClaimStatus.FAILED: {ClaimStatus.ANALYZING},
}

DOCUMENT_EVIDENCE_CATEGORIES = (
    EvidenceCategory.ID_CARD,
    EvidenceCategory.INSURANCE_POLICY,
    EvidenceCategory.VEHICLE_REGISTRATION,
    EvidenceCategory.DRIVER_LICENSE,
)


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
        llm_copilot: LlmCopilotService,
        llm_model: str | None,
        vehicle_manufacturers: VehicleManufacturerService,
        document_analysis: DocumentAnalysisAdapter,
        document_ocr: DocumentOcrAdapter,
        use_mock_document_fields: bool,
        document_extraction: DocumentExtractionService,
        document_field_validation: DocumentFieldValidationService,
        claim_consistency: ClaimConsistencyService,
    ):
        self.claims = ClaimRepository(session)
        self.claim_incidents = ClaimIncidentRepository(session)
        self.evidence = EvidenceRepository(session)
        self.damage_analyses = DamageAnalysisRepository(session)
        self.copilot_conclusions = CopilotConclusionRepository(session)
        self.copilot_conclusion_reviews = CopilotConclusionReviewRepository(session)
        self.workflow_ai_reviews = WorkflowAiReviewRepository(session)
        self.storage = storage
        self.damage_model = damage_model
        self.assessment = assessment
        self.rules = rules
        self.part_search = part_search
        self.llm_copilot = llm_copilot
        self.llm_model = llm_model
        self.vehicle_manufacturers = vehicle_manufacturers
        self.claim_consistency = claim_consistency
        self.analysis_runs = AnalysisRunRepository(session)
        self.analysis_snapshots = AnalysisSnapshotRepository(session)
        self.document_pipeline = DocumentAnalysisPipeline(
            self.analysis_runs,
            storage,
            document_analysis,
            document_ocr,
            use_mock_document_fields,
            document_extraction,
            document_field_validation,
            claim_consistency,
        )
        self.workflow = WorkflowAnalysisOperations(
            self.claims,
            self.claim_incidents,
            self.evidence,
            self.analysis_runs,
            self.damage_analyses,
            damage_model,
            assessment,
            rules,
            part_search,
            self.document_pipeline,
        )
        self.snapshots = AnalysisSnapshotOperations(
            self.analysis_runs,
            self.analysis_snapshots,
            self.claim_incidents,
            self.damage_analyses,
            self.evidence,
            claim_consistency,
        )
        self.reviews = ClaimReviewOperations(
            self.claims,
            self.analysis_runs,
            self.analysis_snapshots,
            self.claim_incidents,
            self.damage_analyses,
            self.workflow_ai_reviews,
            self.copilot_conclusions,
            self.copilot_conclusion_reviews,
            llm_copilot,
            llm_model,
        )
        self.responses = ClaimResponseAssembler(
            self.claims,
            self.claim_incidents,
            self.evidence,
            self.damage_analyses,
            self.copilot_conclusions,
            self.copilot_conclusion_reviews,
            self.workflow_ai_reviews,
            self.analysis_runs,
            claim_consistency,
            self.snapshots,
        )

    def create_claim(self, data: ClaimCreateRequest, created_by: User) -> ClaimResponse:
        if not self.vehicle_manufacturers.is_active_name(data.vehicle.make):
            raise ClaimValidationError("Vehicle manufacturer is unavailable for new claims")
        claim = self.claims.create(data, created_by.id)
        if data.incident:
            self.claim_incidents.save(claim, data.incident)
            self.claims.session.commit()
        return self._to_response(claim)

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

    def update_claim_information(
        self, claim_number: str, data: ClaimInformationUpdateRequest
    ) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        if claim.status in {ClaimStatus.ANALYZING, ClaimStatus.AI_APPROVED, ClaimStatus.AI_REJECTED}:
            raise ClaimValidationError("Claim information cannot be edited in its current state")
        if not self.vehicle_manufacturers.is_active_name(data.vehicle.make):
            raise ClaimValidationError("Vehicle manufacturer is unavailable for claim editing")
        self.claims.update_information(claim, data)
        self.claim_incidents.save(claim, data.incident)
        self.claims.session.commit()
        self.claims.session.refresh(claim)
        return self._to_response(claim)

    def transition_claim(self, claim_number: str, next_status: ClaimStatus) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        if next_status not in ALLOWED_LIFECYCLE_TRANSITIONS.get(claim.status, set()):
            raise ClaimValidationError("Invalid claim lifecycle transition")
        return self._to_response(self.claims.update_status(claim, next_status))

    def start_workflow_analysis(self, claim_number: str) -> WorkflowAnalysisRunResponse | None:
        run = self.workflow.start_workflow_analysis(claim_number)
        return self._to_analysis_run_response(claim_number, run) if run else None

    def process_workflow_analysis(self, run_id: int) -> None:
        self.workflow.process_workflow_analysis(run_id)

    def update_document_analysis_field(
        self,
        claim_number: str,
        document_analysis_id: int,
        field_id: int,
        request: DocumentAnalysisFieldUpdateRequest,
    ) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        document = self.analysis_runs.find_document_for_claim(claim.id, document_analysis_id)
        if document is None:
            raise ClaimResourceNotFoundError("Document analysis not found")
        if self.workflow_ai_reviews.find_for_run(document.analysis_run_id):
            raise ClaimValidationError("Re-run analysis before changing fields after AI review")
        if self.analysis_runs.update_field(document, field_id, request.reviewed_value) is None:
            raise ClaimResourceNotFoundError("Document analysis field not found")
        self.analysis_snapshots.mark_stale(document.analysis_run_id)
        return self._to_response(claim)

    def update_document_field_validation(
        self,
        claim_number: str,
        run_id: int,
        field_validation_id: int,
        request: DocumentFieldValidationUpdateRequest,
    ) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        validation = self.analysis_runs.find_field_validation_for_claim(
            claim.id, run_id, field_validation_id
        )
        if validation is None:
            raise ClaimResourceNotFoundError("Document field validation not found")
        if self.workflow_ai_reviews.find_for_run(run_id):
            raise ClaimValidationError("Re-run analysis before changing fields after AI review")

        validation = self.analysis_runs.update_field_validation(
            validation, request.reviewed_value
        )
        consistency = self.claim_consistency.compare(
            ClaimFacts(
                claimant_name=claim.claimant_name,
                vehicle_make=claim.vehicle_make,
                license_plate=claim.license_plate,
            ),
            [
                ValidatedDocumentField(
                    field_key=validation.field_key,
                    source_evidence_id=validation.source_evidence_id,
                    ocr_value=validation.ocr_value,
                    normalized_value=validation.normalized_value,
                    status=validation.status,
                    confidence=validation.confidence,
                    summary=validation.summary,
                    warnings=json.loads(validation.warnings_json),
                    prompt_version=validation.prompt_version,
                )
            ],
        )
        if consistency:
            self.analysis_runs.update_consistency_check(validation, consistency[0])
        self.analysis_snapshots.mark_stale(run_id)
        return self._to_response(claim)

    def update_document_extracted_field(
        self,
        claim_number: str,
        run_id: int,
        extracted_field_id: int,
        request: DocumentExtractedFieldUpdateRequest,
    ) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        field = self.analysis_runs.find_extracted_field_for_claim(
            claim.id, run_id, extracted_field_id
        )
        if field is None:
            raise ClaimResourceNotFoundError("Document extracted field not found")
        if self.workflow_ai_reviews.find_for_run(run_id):
            raise ClaimValidationError("Re-run analysis before changing fields after AI review")
        self.analysis_runs.update_extracted_field(field, request.confirmed_value)
        self.analysis_snapshots.mark_stale(run_id)
        return self._to_response(claim)

    def update_document_extracted_fields(
        self,
        claim_number: str,
        run_id: int,
        request: DocumentExtractedFieldsBatchUpdateRequest,
    ) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        run = self.analysis_runs.find(run_id)
        if run is None or run.claim_id != claim.id:
            raise ClaimResourceNotFoundError("Analysis run not found")
        if self.workflow_ai_reviews.find_for_run(run_id):
            raise ClaimValidationError("Re-run analysis before changing fields after AI review")
        field_ids = [item.id for item in request.fields]
        fields = self.analysis_runs.find_extracted_fields_for_claim(
            claim.id, run_id, field_ids
        )
        if len(fields) != len(field_ids):
            raise ClaimResourceNotFoundError("One or more document extracted fields were not found")
        all_fields = self.analysis_runs.extracted_fields(run_id)
        if set(field_ids) != {field.id for field in all_fields}:
            raise AnalysisConfirmationBlockedError(
                [
                    AnalysisBlockedReasonResponse(
                        code="REQUIRED_VALUE_MISSING",
                        message="Save All must include every extracted document field.",
                    )
                ]
            )
        values_by_id = {
            item.id: item.confirmed_value.strip() if item.confirmed_value else ""
            for item in request.fields
        }
        reasons = self.snapshots.blocked_reasons(claim, run, values_by_id)
        if reasons:
            raise AnalysisConfirmationBlockedError(reasons)
        payload = self.snapshots.build_payload(claim, run, values_by_id)
        self.analysis_snapshots.save_ready(run, all_fields, values_by_id, payload)
        return self._to_response(claim)

    def run_workflow_ai_review(self, claim_number: str, run_id: int) -> ClaimResponse | None:
        claim = self.reviews.run_workflow_ai_review(claim_number, run_id)
        return self._to_response(claim) if claim else None

    def review_copilot_conclusion(
        self,
        claim_number: str,
        conclusion_id: int,
        request: CopilotConclusionReviewRequest,
        reviewer: User,
    ) -> ClaimResponse | None:
        claim = self.reviews.review_copilot_conclusion(claim_number, conclusion_id, request, reviewer)
        return self._to_response(claim) if claim else None

    def revert_copilot_conclusion_review(
        self,
        claim_number: str,
        conclusion_id: int,
        request: CopilotConclusionReviewRevertRequest,
        reviewer: User,
    ) -> ClaimResponse | None:
        claim = self.reviews.revert_copilot_conclusion_review(claim_number, conclusion_id, request, reviewer)
        return self._to_response(claim) if claim else None

    def upload_evidence(
        self,
        claim_number: str,
        categories: list[EvidenceCategory],
        files: list[UploadFile],
        other_document_label: str | None = None,
    ) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        if claim.status in {ClaimStatus.ANALYZING, ClaimStatus.AI_APPROVED, ClaimStatus.AI_REJECTED}:
            raise ClaimValidationError("Evidence cannot be changed in the claim's current state")
        if len(files) != len(categories):
            raise ClaimValidationError("Each uploaded file must have exactly one evidence category")
        if any(
            category is EvidenceCategory.VEHICLE_DAMAGE_IMAGE
            and Path(upload.filename or "").suffix.lower() == ".pdf"
            for category, upload in zip(categories, files, strict=True)
        ):
            raise ClaimValidationError("Vehicle damage evidence must be an image")
        if len(self.evidence.list_for_claim(claim.id)) + len(files) > self.storage.max_files:
            raise ClaimValidationError(f"A claim may have at most {self.storage.max_files} evidence files")
        has_other_documents = EvidenceCategory.OTHER_DOCUMENT in categories
        if has_other_documents and not (other_document_label and other_document_label.strip()):
            raise ClaimValidationError("Other documents require a document name")
        if other_document_label and not has_other_documents:
            raise ClaimValidationError("A document name can only be used with other documents")

        stored_uploads = self.storage.save_all(claim_number, files)
        uploads = list(zip(categories, stored_uploads, strict=True))
        try:
            self.evidence.create_many(claim, uploads, other_document_label.strip() if other_document_label else None)
            self.claim_incidents.touch(claim.id)
            self.claims.session.commit()
        except SQLAlchemyError as error:
            self.claims.session.rollback()
            self.storage.delete_stored(stored_uploads)
            raise EvidencePersistenceError("Unable to persist uploaded evidence") from error

        return self._to_response(claim)

    def delete_evidence(self, claim_number: str, evidence_id: int) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        if claim.status in {ClaimStatus.ANALYZING, ClaimStatus.AI_APPROVED, ClaimStatus.AI_REJECTED}:
            raise ClaimValidationError("Evidence cannot be changed in the claim's current state")
        item = self.evidence.find_for_claim(claim.id, evidence_id)
        if item is None:
            raise ClaimResourceNotFoundError("Evidence not found")
        stored_path = item.stored_path
        if self.evidence.is_referenced_by_analysis(item.id):
            self.evidence.mark_removed(item)
        else:
            self.evidence.delete(item)
            self.storage.delete(stored_path)
        self.claim_incidents.touch(claim.id)
        self.claims.session.commit()
        return self._to_response(claim)

    def evidence_content_path(self, claim_number: str, evidence_id: int) -> tuple[Evidence, Path] | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        evidence = self.evidence.find_any_for_claim(claim.id, evidence_id)
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
            raise ClaimValidationError("Upload at least one vehicle damage image before running analysis")
        model_result = self.damage_model.analyze(images)
        detections = model_result.detections
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
            model_result,
            detections,
            rules,
            reference_prices,
        )
        conclusion = self.llm_copilot.generate(
            self._copilot_input(claim, assessment.assessment, assessment.warning, detections, reference_prices)
        )
        provider_model = self.llm_model if conclusion.status is CopilotConclusionStatus.GENERATED else None
        self.copilot_conclusions.create(analysis, conclusion, provider_model)
        return self._to_damage_analysis_response(claim.claim_number, analysis)

    def _to_response(self, claim: Claim) -> ClaimResponse:
        return self.responses._to_response(claim)

    def _to_analysis_run_response(
        self, claim_number: str, run: WorkflowAnalysisRun
    ) -> WorkflowAnalysisRunResponse:
        return self.responses._to_analysis_run_response(claim_number, run)

    def _to_damage_analysis_response(
        self, claim_number: str, analysis: DamageAnalysis
    ) -> DamageAnalysisResponse:
        return self.responses._to_damage_analysis_response(claim_number, analysis)

    @staticmethod
    def _copilot_input(
        claim: Claim,
        assessment: DamageAssessment,
        warning: str | None,
        detections: list[DamageModelDetection],
        reference_prices: list[ReferencePartPriceResult],
    ) -> CopilotInput:
        return CopilotInput(
            context=AiReviewContext(
                claim=AiReviewClaimFacts(
                    claim_number=claim.claim_number,
                    status=claim.status.value,
                    claimant_name=claim.claimant_name,
                ),
                vehicle=AiReviewVehicleFacts(
                    make=claim.vehicle_make,
                    model=claim.vehicle_model,
                    year=claim.vehicle_year,
                    license_plate=claim.license_plate,
                    vin=claim.vin,
                ),
                documents={},
                damage=AiReviewDamage(
                    assessment=assessment.value,
                    warning=warning,
                    findings=[
                        AiReviewDamageFinding(
                            part=detection.vehicle_part,
                            damage_type=detection.damage_type,
                            area_percentage=detection.damage_percentage,
                        )
                        for detection in detections
                    ],
                ),
                warnings=[warning] if warning else [],
                reference_prices=[
                    AiReviewReferencePrice(
                        part=price.part_identity,
                        amount=price.amount,
                        currency=price.currency,
                        source_name=price.source_name,
                        price_type=price.price_type,
                        status=price.status.value,
                    )
                    for price in reference_prices
                ],
            )
        )
