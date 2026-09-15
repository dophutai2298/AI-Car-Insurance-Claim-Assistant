import json
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import (
    AnalysisResultStatus,
    AnalysisRunStatus,
    Claim,
    ClaimStatus,
    CopilotConclusionStatus,
    CopilotConclusionReview,
    DamageAssessment,
    DamageAnalysis,
    Evidence,
    EvidenceCategory,
    CopilotConclusion,
    ReferencePartPrice,
    ReferencePriceLookupStatus,
    ReferencePriceStatus,
    User,
    WorkflowAnalysisRun,
)
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.claims import ClaimRepository
from app.repositories.claim_incidents import ClaimIncidentRepository
from app.repositories.damage_analyses import DamageAnalysisRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.copilot_conclusions import CopilotConclusionRepository
from app.repositories.copilot_conclusion_reviews import (
    CopilotConclusionAlreadyReviewedError,
    CopilotConclusionReviewRepository,
)
from app.repositories.workflow_ai_reviews import WorkflowAiReviewRepository
from app.schemas.claims import (
    ClaimCreateRequest,
    ClaimInformationUpdateRequest,
    IncidentInformation,
    CopilotConclusionResponse,
    CopilotConclusionReviewRequest,
    CopilotConclusionReviewRevertRequest,
    CopilotConclusionReviewResponse,
    CopilotFindingResponse,
    DamageAnalysisResponse,
    DamageDetectionResponse,
    ClaimListItem,
    ClaimResponse,
    EvidenceResponse,
    EvidenceReferenceResponse,
    DocumentAnalysisFieldResponse,
    DocumentAnalysisFieldUpdateRequest,
    DocumentAnalysisResponse,
    DocumentOcrResultResponse,
    ReferencePartPriceResponse,
    VehicleMetadata,
    WorkflowAnalysisRunResponse,
)
from app.schemas.admin import AssessmentRuleValuesSchema
from app.services.assessment_rules import AssessmentRuleService
from app.services.evidence_storage import EvidenceStorage, EvidenceStorageError, StoredEvidence
from app.services.damage_assessment import DamageAssessmentService
from app.services.damage_model import DamageModelAdapter, DamageModelDetection
from app.services.part_search import PartSearchService, ReferencePartPriceResult
from app.services.llm_copilot import (
    CopilotInput,
    CopilotReferencePrice,
    CopilotStructuredFinding,
    LlmCopilotService,
)
from app.services.vehicle_manufacturers import VehicleManufacturerService
from app.services.document_analysis import DocumentAnalysisAdapter, DocumentAnalysisResult
from app.services.document_ocr import DocumentOcrAdapter, DocumentOcrError

ALLOWED_LIFECYCLE_TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    ClaimStatus.DRAFT: {ClaimStatus.ANALYZING},
    ClaimStatus.ANALYZING: {ClaimStatus.REVIEW_REQUIRED, ClaimStatus.FAILED},
    ClaimStatus.FAILED: {ClaimStatus.ANALYZING},
}

REQUIRED_EVIDENCE_CATEGORIES = (
    EvidenceCategory.VEHICLE_DAMAGE_IMAGE,
    EvidenceCategory.ID_CARD,
    EvidenceCategory.INSURANCE_POLICY,
    EvidenceCategory.VEHICLE_REGISTRATION,
    EvidenceCategory.DRIVER_LICENSE,
)
DOCUMENT_EVIDENCE_CATEGORIES = REQUIRED_EVIDENCE_CATEGORIES[1:]
SUPPORTED_DOCUMENT_IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


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
        self.document_analysis = document_analysis
        self.document_ocr = document_ocr
        self.use_mock_document_fields = use_mock_document_fields
        self.analysis_runs = AnalysisRunRepository(session)

    def create_claim(self, data: ClaimCreateRequest, created_by: User) -> ClaimResponse:
        if not self.vehicle_manufacturers.is_active_name(data.vehicle.make):
            raise ValueError("Vehicle manufacturer is unavailable for new claims")
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
            raise ValueError("Claim information cannot be edited in its current state")
        if not self.vehicle_manufacturers.is_active_name(data.vehicle.make):
            raise ValueError("Vehicle manufacturer is unavailable for claim editing")
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
            raise ValueError("Invalid claim lifecycle transition")
        return self._to_response(self.claims.update_status(claim, next_status))

    def start_workflow_analysis(self, claim_number: str) -> WorkflowAnalysisRunResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        if claim.status in {ClaimStatus.AI_APPROVED, ClaimStatus.AI_REJECTED}:
            raise ValueError("Revert the human review before running analysis again")
        active_run = self.analysis_runs.latest_for_claim(claim.id)
        if active_run and active_run.status in {AnalysisRunStatus.PENDING, AnalysisRunStatus.PROCESSING}:
            raise RuntimeError("Analysis is already running")
        incident = self.claim_incidents.find_for_claim(claim.id)
        if incident is None:
            raise ValueError("Complete incident information before starting analysis")
        evidence = self.evidence.list_for_claim(claim.id)
        uploaded_categories = {item.category for item in evidence}
        missing = [category.value for category in REQUIRED_EVIDENCE_CATEGORIES if category not in uploaded_categories]
        if missing:
            raise ValueError(f"Upload required evidence before starting analysis: {', '.join(missing)}")
        run = self.analysis_runs.create(claim, incident.input_revision)
        return self._to_analysis_run_response(claim.claim_number or claim_number, run)

    def process_workflow_analysis(self, run_id: int) -> None:
        run = self.analysis_runs.find(run_id)
        if run is None or run.status is not AnalysisRunStatus.PENDING:
            return
        claim = self.claims.find_by_id(run.claim_id)
        if claim is None:
            return
        self.analysis_runs.mark_processing(run)
        try:
            self._process_workflow_capabilities(run, claim)
        except Exception as error:
            self.claims.session.rollback()
            self.analysis_runs.fail(run, claim, str(error) or "Analysis processing failed")

    def _process_workflow_capabilities(
        self, run: WorkflowAnalysisRun, claim: Claim
    ) -> None:
        evidence = self.evidence.list_for_claim(claim.id)
        by_category = {
            category: [item for item in evidence if item.category is category]
            for category in REQUIRED_EVIDENCE_CATEGORIES
        }

        try:
            detections = self.damage_model.analyze(by_category[EvidenceCategory.VEHICLE_DAMAGE_IMAGE])
            rules = self.rules.active_values()
            assessment = self.assessment.assess(detections, rules)
            reference_prices = self.part_search.lookup_for_assessment(
                assessment.assessment,
                detections,
                claim.vehicle_make,
                claim.vehicle_model,
                claim.vehicle_year,
                False,
            )
            damage_analysis = self.damage_analyses.create(
                claim,
                assessment,
                detections,
                rules,
                reference_prices,
                update_claim_status=False,
            )
            self.analysis_runs.attach_damage(run, damage_analysis)
        except Exception as error:
            self.analysis_runs.mark_damage_failed(run, str(error) or "Damage analysis failed")

        for category in DOCUMENT_EVIDENCE_CATEGORIES:
            self._process_document_ocr_category(run, category, by_category[category])

        self.analysis_runs.complete(run, claim)

    def _process_document_ocr_category(
        self, run: WorkflowAnalysisRun, category: EvidenceCategory, evidence_items: list[Evidence]
    ) -> None:
        ocr_records = [
            (item, self.analysis_runs.create_document_ocr_result(run, item))
            for item in evidence_items
        ]
        warnings: list[str] = []
        statuses: list[AnalysisResultStatus] = []

        for evidence, record in ocr_records:
            self.analysis_runs.update_document_ocr_result(record, AnalysisResultStatus.PROCESSING)
            if not self._supports_document_image(evidence):
                warning = "Only supported image evidence can be processed by OCR; this file was skipped."
                self.analysis_runs.update_document_ocr_result(
                    record, AnalysisResultStatus.FAILED, warning=warning
                )
                warnings.append(f"{evidence.original_filename}: {warning}")
                statuses.append(AnalysisResultStatus.FAILED)
                continue
            try:
                extracted = self.document_ocr.extract(
                    evidence, self.storage.resolve_path(evidence.stored_path)
                )
                self.analysis_runs.update_document_ocr_result(
                    record,
                    AnalysisResultStatus.COMPLETED,
                    raw_text=extracted.raw_text,
                    adapter_name=extracted.adapter_name,
                    adapter_metadata=extracted.metadata,
                    warning=extracted.warning,
                )
                if extracted.warning:
                    warnings.append(f"{evidence.original_filename}: {extracted.warning}")
                statuses.append(AnalysisResultStatus.COMPLETED)
            except (DocumentOcrError, EvidenceStorageError) as error:
                warning = str(error) or "OCR processing failed."
                self.analysis_runs.update_document_ocr_result(
                    record, AnalysisResultStatus.FAILED, warning=warning
                )
                warnings.append(f"{evidence.original_filename}: {warning}")
                statuses.append(AnalysisResultStatus.FAILED)
            except Exception:
                warning = "OCR processing failed unexpectedly."
                self.analysis_runs.update_document_ocr_result(
                    record, AnalysisResultStatus.FAILED, warning=warning
                )
                warnings.append(f"{evidence.original_filename}: {warning}")
                statuses.append(AnalysisResultStatus.FAILED)

        category_status = self._document_category_status(statuses)
        fallback_result: DocumentAnalysisResult | None = None
        if self.use_mock_document_fields and category_status is not AnalysisResultStatus.FAILED:
            try:
                fallback_result = self.document_analysis.analyze(category, evidence_items)
            except Exception as error:
                warnings.append(str(error) or "Mock document analysis failed.")

        self.analysis_runs.save_document_result(
            run,
            category,
            category_status,
            result=fallback_result,
            warning="; ".join(warnings) if warnings else None,
        )

    @staticmethod
    def _document_category_status(statuses: list[AnalysisResultStatus]) -> AnalysisResultStatus:
        if statuses and all(status is AnalysisResultStatus.COMPLETED for status in statuses):
            return AnalysisResultStatus.COMPLETED
        if any(status is AnalysisResultStatus.COMPLETED for status in statuses):
            return AnalysisResultStatus.PARTIAL
        return AnalysisResultStatus.FAILED

    @staticmethod
    def _supports_document_image(evidence: Evidence) -> bool:
        suffix = Path(evidence.original_filename).suffix.lower()
        content_type = (evidence.content_type or "").lower()
        return suffix in SUPPORTED_DOCUMENT_IMAGE_EXTENSIONS and (
            not content_type or content_type.startswith("image/")
        )

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
            raise LookupError("Document analysis not found")
        if self.workflow_ai_reviews.find_for_run(document.analysis_run_id):
            raise ValueError("Re-run analysis before changing fields after AI review")
        if self.analysis_runs.update_field(document, field_id, request.reviewed_value) is None:
            raise LookupError("Document analysis field not found")
        return self._to_response(claim)

    def run_workflow_ai_review(self, claim_number: str, run_id: int) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        run = self.analysis_runs.find(run_id)
        if run is None or run.claim_id != claim.id:
            raise LookupError("Analysis run not found")
        if run.status not in {AnalysisRunStatus.COMPLETED, AnalysisRunStatus.PARTIAL}:
            raise ValueError("Analysis results are not ready for AI review")
        if self.workflow_ai_reviews.find_for_run(run.id):
            raise RuntimeError("AI review has already been generated for this analysis")
        incident_record = self.claim_incidents.find_for_claim(claim.id)
        if incident_record is None or incident_record.input_revision != run.input_revision:
            raise ValueError("Claim information or evidence changed; run analysis again")
        damage = self.analysis_runs.damage_analysis(run.id)
        if damage is None:
            raise ValueError("Damage analysis is required before AI review")

        detections = self.damage_analyses.list_detections(damage.id)
        reference_prices = self.damage_analyses.reference_prices(damage.id)
        documents = self.analysis_runs.documents(run.id)
        document_payload: list[dict[str, object]] = []
        warnings = [damage.warning] if damage.warning else []
        for document in documents:
            document_warnings = json.loads(document.warnings_json)
            warnings.extend(document_warnings)
            document_payload.append(
                {
                    "document_type": document.document_type.value,
                    "status": document.status.value,
                    "fields": [
                        {
                            "key": field.key,
                            "original_ai_value": field.original_ai_value,
                            "reviewed_value": field.reviewed_value,
                            "confidence": field.confidence,
                            "status": field.status.value,
                        }
                        for field in self.analysis_runs.fields(document.id)
                    ],
                    "warnings": document_warnings,
                }
            )
        evidence = self.evidence.list_for_claim(claim.id)
        evidence_references = [
            {
                "id": item.id,
                "category": item.category.value,
                "original_filename": item.original_filename,
            }
            for item in evidence
        ]
        incident = self._incident_response(claim.id)
        input_data = CopilotInput(
            vehicle_summary=f"{claim.vehicle_year} {claim.vehicle_make} {claim.vehicle_model}",
            assessment=damage.assessment,
            warning=damage.warning,
            findings=[
                CopilotStructuredFinding(
                    vehicle_part=item.vehicle_part,
                    damage_type=item.damage_type,
                    damage_percentage=item.damage_percentage,
                    confidence=item.confidence,
                )
                for item in detections
            ],
            reference_prices=[
                CopilotReferencePrice(
                    part_identity=price.part_identity,
                    amount=price.amount,
                    currency=price.currency,
                    source_name=price.source_name,
                    source_url=price.source_url,
                    price_type=price.price_type,
                    status=price.status,
                )
                for price in reference_prices
            ],
            claim={"id": claim.claim_number, "status": claim.status.value},
            vehicle={
                "make": claim.vehicle_make,
                "model": claim.vehicle_model,
                "year": claim.vehicle_year,
                "license_plate": claim.license_plate,
                "vin": claim.vin,
            },
            claimant={"name": claim.claimant_name},
            incident=incident.model_dump(mode="json") if incident else None,
            document_analysis=document_payload,
            warnings=warnings,
            evidence_references=evidence_references,
        )
        result = self.llm_copilot.generate(input_data)
        provider_model = self.llm_model if result.status is CopilotConclusionStatus.GENERATED else None
        conclusion = self.copilot_conclusions.create(damage, result, provider_model)
        failed_documents = sum(
            document.status is AnalysisResultStatus.FAILED for document in documents
        )
        validity_percentage = max(0, min(100, 85 - failed_documents * 15 - len(warnings) * 5))
        self.workflow_ai_reviews.create(
            run.id,
            conclusion,
            validity_percentage,
            warnings,
            evidence_references,
        )
        return self._to_response(claim)

    def review_copilot_conclusion(
        self,
        claim_number: str,
        conclusion_id: int,
        request: CopilotConclusionReviewRequest,
        reviewer: User,
    ) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        conclusion = self.copilot_conclusions.find_for_claim(claim.id, conclusion_id)
        if conclusion is None:
            raise LookupError("AI conclusion not found")
        if self.copilot_conclusion_reviews.exists_for_conclusion(conclusion.id):
            raise RuntimeError("AI conclusion has already been reviewed")
        if claim.status is not ClaimStatus.REVIEW_REQUIRED:
            raise ValueError("Claim is not awaiting AI conclusion review")
        latest_analysis = self.damage_analyses.latest_for_claim(claim.id)
        if latest_analysis is None or conclusion.analysis_id != latest_analysis.id:
            raise ValueError("AI conclusion is not current")
        try:
            self.copilot_conclusion_reviews.create(claim, conclusion, request, reviewer)
        except CopilotConclusionAlreadyReviewedError as error:
            raise RuntimeError("AI conclusion has already been reviewed") from error
        return self._to_response(claim)

    def revert_copilot_conclusion_review(
        self,
        claim_number: str,
        conclusion_id: int,
        request: CopilotConclusionReviewRevertRequest,
        reviewer: User,
    ) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        review = self.copilot_conclusion_reviews.find_for_conclusion(conclusion_id)
        if review is None or review.claim_id != claim.id:
            raise LookupError("AI conclusion review not found")
        if self.copilot_conclusion_reviews.reversion_for_review(review.id):
            raise RuntimeError("AI conclusion review has already been reverted")
        self.copilot_conclusion_reviews.revert(claim, review, reviewer, request.note)
        return self._to_response(claim)

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
            raise ValueError("Evidence cannot be changed in the claim's current state")
        if len(files) != len(categories):
            raise ValueError("Each uploaded file must have exactly one evidence category")
        has_other_documents = EvidenceCategory.OTHER_DOCUMENT in categories
        if has_other_documents and not (other_document_label and other_document_label.strip()):
            raise ValueError("Other documents require a document name")
        if other_document_label and not has_other_documents:
            raise ValueError("A document name can only be used with other documents")

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
            raise ValueError("Evidence cannot be changed in the claim's current state")
        item = self.evidence.find_for_claim(claim.id, evidence_id)
        if item is None:
            raise LookupError("Evidence not found")
        stored_path = item.stored_path
        if self.evidence.is_referenced_by_damage_analysis(item.id):
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
        conclusion = self.llm_copilot.generate(
            self._copilot_input(claim, assessment.assessment, assessment.warning, detections, reference_prices)
        )
        provider_model = self.llm_model if conclusion.status is CopilotConclusionStatus.GENERATED else None
        self.copilot_conclusions.create(analysis, conclusion, provider_model)
        return self._to_damage_analysis_response(claim.claim_number, analysis)

    def _to_response(self, claim: Claim) -> ClaimResponse:
        if claim.claim_number is None:
            raise ValueError("Claim number must be assigned before serialization")

        evidence_groups = self.evidence.group_details_for_claim(claim.id)
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
            incident=self._incident_response(claim.id),
            status=claim.status,
            created_at=claim.created_at,
            updated_at=claim.updated_at,
            evidence=[
                self._to_evidence_response(claim.claim_number, item, evidence_groups.get(item.id))
                for item in self.evidence.list_for_claim(claim.id)
            ],
            latest_damage_analysis=self._latest_damage_analysis_response(claim.claim_number, claim.id),
            latest_analysis_run=self._latest_analysis_run_response(claim.claim_number, claim.id),
            copilot_review_history=[
                self._to_copilot_conclusion_review_response(claim.claim_number, item, reviewer)
                for item, reviewer in self.copilot_conclusion_reviews.list_for_claim(claim.id)
            ],
        )

    def _latest_analysis_run_response(
        self, claim_number: str, claim_id: int
    ) -> WorkflowAnalysisRunResponse | None:
        run = self.analysis_runs.latest_for_claim(claim_id)
        return self._to_analysis_run_response(claim_number, run) if run else None

    def _to_analysis_run_response(
        self, claim_number: str, run: WorkflowAnalysisRun
    ) -> WorkflowAnalysisRunResponse:
        damage = self.analysis_runs.damage_analysis(run.id)
        incident = self.claim_incidents.find_for_claim(run.claim_id)
        return WorkflowAnalysisRunResponse(
            id=run.id,
            status=run.status,
            damage_status=run.damage_status,
            damage_analysis=self._to_damage_analysis_response(claim_number, damage) if damage else None,
            document_analyses=[
                DocumentAnalysisResponse(
                    id=document.id,
                    document_type=document.document_type,
                    status=document.status,
                    fields=[
                        DocumentAnalysisFieldResponse(
                            id=field.id,
                            key=field.key,
                            label=field.label,
                            original_ai_value=field.original_ai_value,
                            reviewed_value=field.reviewed_value,
                            confidence=field.confidence,
                            status=field.status,
                        )
                        for field in self.analysis_runs.fields(document.id)
                    ],
                    warnings=json.loads(document.warnings_json),
                )
                for document in self.analysis_runs.documents(run.id)
            ],
            document_ocr_results=[
                DocumentOcrResultResponse(
                    id=result.id,
                    source_evidence_id=result.evidence_id,
                    document_type=result.document_type,
                    original_filename=result.original_filename,
                    content_type=result.content_type,
                    status=result.status,
                    raw_text=result.raw_text,
                    adapter_name=result.adapter_name,
                    adapter_metadata=json.loads(result.adapter_metadata_json),
                    warning=result.warning,
                    created_at=result.created_at,
                    processed_at=result.processed_at,
                )
                for result in self.analysis_runs.document_ocr_results(run.id)
            ],
            failure_reason=run.failure_reason,
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
            inputs_changed=incident is None or incident.input_revision != run.input_revision,
        )

    def _incident_response(self, claim_id: int) -> IncidentInformation | None:
        incident = self.claim_incidents.find_for_claim(claim_id)
        if incident is None:
            return None
        occurred_at = incident.occurred_at
        if occurred_at.tzinfo is None:
            from datetime import timezone

            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        return IncidentInformation(
            occurred_at=occurred_at,
            location=incident.location,
            description=incident.description,
        )

    def _latest_damage_analysis_response(self, claim_number: str, claim_id: int) -> DamageAnalysisResponse | None:
        analysis = self.damage_analyses.latest_for_claim(claim_id)
        return self._to_damage_analysis_response(claim_number, analysis) if analysis else None

    def _to_damage_analysis_response(self, claim_number: str, analysis: DamageAnalysis) -> DamageAnalysisResponse:
        if analysis.analysis_number is None:
            raise ValueError("Damage analysis number must be assigned before serialization")
        evidence_by_id = {item.id: item for item in self.evidence.list_all_for_claim(analysis.claim_id)}
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
        reference_price_responses = [self._to_reference_price_response(price) for price in reference_prices]
        return DamageAnalysisResponse(
            id=analysis.analysis_number,
            assessment=analysis.assessment,
            warning=analysis.warning,
            detections=detections,
            rules=self._rules_for_analysis(analysis.id),
            reference_price_status=self._reference_price_status(reference_prices),
            reference_prices=reference_price_responses,
            copilot_conclusion=self._to_copilot_conclusion_response(
                claim_number,
                self.copilot_conclusions.find_for_analysis(analysis.id),
                detections,
                reference_price_responses,
                analysis.warning,
            ),
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

    @staticmethod
    def _copilot_input(
        claim: Claim,
        assessment: DamageAssessment,
        warning: str | None,
        detections: list[DamageModelDetection],
        reference_prices: list[ReferencePartPriceResult],
    ) -> CopilotInput:
        return CopilotInput(
            vehicle_summary=f"{claim.vehicle_year} {claim.vehicle_make} {claim.vehicle_model}",
            assessment=assessment,
            warning=warning,
            findings=[
                CopilotStructuredFinding(
                    vehicle_part=detection.vehicle_part,
                    damage_type=detection.damage_type,
                    damage_percentage=detection.damage_percentage,
                    confidence=detection.confidence,
                )
                for detection in detections
            ],
            reference_prices=[
                CopilotReferencePrice(
                    part_identity=price.part_identity,
                    amount=price.amount,
                    currency=price.currency,
                    source_name=price.source_name,
                    source_url=price.source_url,
                    price_type=price.price_type,
                    status=price.status,
                )
                for price in reference_prices
            ],
        )

    def _to_copilot_conclusion_response(
        self,
        claim_number: str,
        conclusion: CopilotConclusion | None,
        detections: list[DamageDetectionResponse],
        reference_prices: list[ReferencePartPriceResponse],
        warning: str | None,
    ) -> CopilotConclusionResponse | None:
        if conclusion is None:
            return None
        workflow_review = self.workflow_ai_reviews.find_for_conclusion(conclusion.id)
        workflow_warnings = json.loads(workflow_review.warnings_json) if workflow_review else []
        evidence_references = (
            [
                EvidenceReferenceResponse.model_validate(item)
                for item in json.loads(workflow_review.evidence_references_json)
            ]
            if workflow_review
            else []
        )
        return CopilotConclusionResponse(
            id=conclusion.id,
            status=conclusion.status,
            recommendation=conclusion.recommendation,
            summary=conclusion.summary,
            fallback_summary=conclusion.fallback_summary,
            failure_reason=conclusion.failure_reason,
            provider_model=conclusion.provider_model,
            findings=[
                CopilotFindingResponse(
                    vehicle_part=detection.vehicle_part,
                    damage_type=detection.damage_type,
                    damage_percentage=detection.damage_percentage,
                    confidence=detection.confidence,
                    annotated_evidence=detection.annotated_evidence,
                )
                for detection in detections
            ],
            warnings=workflow_warnings or ([warning] if warning else []),
            reference_prices=reference_prices,
            review_history=[
                self._to_copilot_conclusion_review_response(claim_number, item, reviewer)
                for item, reviewer in self.copilot_conclusion_reviews.list_for_conclusion(conclusion.id)
            ],
            validity_percentage=workflow_review.validity_percentage if workflow_review else None,
            review_status=workflow_review.review_status if workflow_review else None,
            evidence_references=evidence_references,
        )

    def _to_copilot_conclusion_review_response(
        self, claim_number: str, review: CopilotConclusionReview, reviewer: str
    ) -> CopilotConclusionReviewResponse:
        reversion = self.copilot_conclusion_reviews.reversion_for_review(review.id)
        return CopilotConclusionReviewResponse(
            claim_id=claim_number,
            conclusion_id=review.conclusion_id,
            status=review.status,
            reason_category=review.reason_category,
            comment=review.comment,
            reviewer=reviewer,
            reviewed_at=review.reviewed_at,
            reverted_at=reversion[0].reverted_at if reversion else None,
            reverted_by=reversion[1] if reversion else None,
            revert_note=reversion[0].note if reversion else None,
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
    def _to_evidence_response(
        claim_number: str,
        evidence: Evidence,
        group: tuple[int, str] | None = None,
    ) -> EvidenceResponse:
        return EvidenceResponse(
            id=evidence.id,
            category=evidence.category,
            original_filename=evidence.original_filename,
            content_type=evidence.content_type,
            file_size=evidence.file_size,
            uploaded_at=evidence.uploaded_at,
            content_url=f"/api/claims/{claim_number}/evidence/{evidence.id}/content",
            group_id=group[0] if group else None,
            group_label=group[1] if group else None,
        )
