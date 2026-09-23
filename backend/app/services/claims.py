import json
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import (
    AnalysisResultStatus,
    AnalysisRunStatus,
    AnalysisSnapshotStatus,
    Claim,
    DocumentExtractedField,
    DocumentFieldValidation,
    ClaimStatus,
    CopilotConclusionStatus,
    CopilotConclusionReview,
    DamageAssessment,
    DamageAnalysis,
    DocumentOcrResult,
    Evidence,
    EvidenceCategory,
    ConsistencyStatus,
    CopilotConclusion,
    ReferencePartPrice,
    ReferencePriceLookupStatus,
    ReferencePriceStatus,
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
    DocumentExtractedFieldResponse,
    DocumentExtractedFieldsBatchUpdateRequest,
    DocumentExtractedFieldUpdateRequest,
    DocumentFieldComparisonResponse,
    DocumentExtractionResultResponse,
    DocumentOcrResultResponse,
    DocumentFieldValidationResponse,
    DocumentFieldValidationUpdateRequest,
    ClaimConsistencyCheckResponse,
    ReferencePartPriceResponse,
    VehicleMetadata,
    WorkflowAnalysisRunResponse,
    AnalysisBlockedReasonResponse,
    AnalysisReadinessResponse,
    AiReviewStructuredResponse,
    ConfirmedAnalysisSnapshotResponse,
)
from app.schemas.admin import AssessmentRuleValuesSchema
from app.services.assessment_rules import AssessmentRuleService
from app.services.evidence_storage import EvidenceStorage, EvidenceStorageError, StoredEvidence
from app.services.damage_assessment import DamageAssessmentService
from app.services.damage_model import DamageModelAdapter, DamageModelDetection
from app.services.part_search import PartSearchService, ReferencePartPriceResult
from app.services.llm_copilot import (
    AiReviewClaimFacts,
    AiReviewContext,
    AiReviewDamage,
    AiReviewDamageFinding,
    AiReviewDocument,
    AiReviewDocumentField,
    AiReviewIncidentFacts,
    AiReviewReferencePrice,
    AiReviewVehicleFacts,
    CopilotInput,
    LlmCopilotService,
)
from app.services.vehicle_manufacturers import VehicleManufacturerService
from app.services.document_analysis import DocumentAnalysisAdapter, DocumentAnalysisResult
from app.services.document_ocr import DocumentOcrAdapter, DocumentOcrError
from app.services.document_consistency import (
    ClaimConsistencyService,
    ClaimFacts,
    ConsistencyResult,
)
from app.services.document_extraction import DocumentExtractionService
from app.services.document_extraction import SCHEMA_VERSION as DOCUMENT_EXTRACTION_SCHEMA_VERSION
from app.services.document_field_validation import (
    DocumentFieldValidationService,
    ValidatedDocumentField,
)

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


class AnalysisConfirmationBlockedError(Exception):
    def __init__(self, reasons: list[AnalysisBlockedReasonResponse]):
        super().__init__("Analysis confirmation is blocked")
        self.reasons = reasons

    def detail(self) -> dict[str, object]:
        return {
            "message": str(self),
            "blocked_reasons": [reason.model_dump(mode="json") for reason in self.reasons],
        }


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
        self.document_analysis = document_analysis
        self.document_ocr = document_ocr
        self.use_mock_document_fields = use_mock_document_fields
        self.document_extraction = document_extraction
        self.document_field_validation = document_field_validation
        self.claim_consistency = claim_consistency
        self.analysis_runs = AnalysisRunRepository(session)
        self.analysis_snapshots = AnalysisSnapshotRepository(session)

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
            model_result = self.damage_model.analyze(
                by_category[EvidenceCategory.VEHICLE_DAMAGE_IMAGE]
            )
            detections = model_result.detections
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
                model_result,
                detections,
                rules,
                reference_prices,
                update_claim_status=False,
            )
            self.analysis_runs.attach_damage(run, damage_analysis)
        except Exception as error:
            self.analysis_runs.mark_damage_failed(run, str(error) or "Damage analysis failed")

        previous_run = self.analysis_runs.latest_before(claim.id, run.id)
        ocr_by_category = {
            category: self._process_document_ocr_category(
                run, category, by_category[category]
            )
            for category in DOCUMENT_EVIDENCE_CATEGORIES
        }

        self._extract_document_fields(run, previous_run, ocr_by_category)
        self._validate_document_fields(run, claim)

        self.analysis_runs.complete(run, claim)

    def _extract_document_fields(
        self,
        run: WorkflowAnalysisRun,
        previous_run: WorkflowAnalysisRun | None,
        ocr_by_category: dict[EvidenceCategory, list[DocumentOcrResult]],
    ) -> None:
        for category, ocr_results in ocr_by_category.items():
            completed = [
                result
                for result in ocr_results
                if result.status is AnalysisResultStatus.COMPLETED and result.raw_text
            ]
            if not completed or not self.document_extraction.supports(category):
                continue
            previous_ocr = (
                [
                    result
                    for result in self.analysis_runs.document_ocr_results(previous_run.id)
                    if result.document_type is category
                ]
                if previous_run
                else []
            )
            unchanged = {result.evidence_id for result in previous_ocr} == {
                result.evidence_id for result in ocr_results
            }
            previous_extraction = (
                self.analysis_runs.document_extraction_for_category(
                    previous_run.id,
                    category,
                    DOCUMENT_EXTRACTION_SCHEMA_VERSION,
                )
                if previous_run and unchanged
                else None
            )
            if (
                previous_extraction is None
                and previous_run
                and unchanged
                and len(ocr_results) == 1
            ):
                previous_extraction = self.analysis_runs.document_extraction_for_category(
                    previous_run.id,
                    category,
                )
            representative = completed[0]
            if previous_extraction is not None:
                self.analysis_runs.copy_document_extraction(
                    run,
                    representative,
                    previous_extraction,
                    DOCUMENT_EXTRACTION_SCHEMA_VERSION,
                )
                self.analysis_runs.mark_document_extraction_reuse(
                    representative,
                    reused=True,
                    source_run_id=previous_extraction.analysis_run_id,
                )
                continue
            combined_ocr = "\n\n".join(
                f"--- SOURCE: {result.original_filename} ---\n{result.raw_text}"
                for result in completed
            )
            outcome = self.document_extraction.extract(
                category,
                combined_ocr,
            )
            self.analysis_runs.save_document_extraction(run, representative, outcome)
            self.analysis_runs.mark_document_extraction_reuse(
                representative, reused=False
            )

    def _validate_document_fields(
        self, run: WorkflowAnalysisRun, claim: Claim
    ) -> None:
        claim_information = {
            "claimant_name": claim.claimant_name,
            "vehicle_make": claim.vehicle_make,
            "license_plate": claim.license_plate or "",
        }
        validated_fields: list[ValidatedDocumentField] = []
        validation_records: list[DocumentFieldValidation] = []
        for ocr_result in self.analysis_runs.document_ocr_results(run.id):
            if (
                ocr_result.status is not AnalysisResultStatus.COMPLETED
                or self.document_extraction.supports(ocr_result.document_type)
            ):
                continue
            validations = self.document_field_validation.validate_ocr_result(
                ocr_result.document_type,
                ocr_result.evidence_id,
                ocr_result.raw_text or "",
                claim_information,
            )
            validated_fields.extend(validations)
            validation_records.extend(
                self.analysis_runs.save_field_validations(run, ocr_result, validations)
            )

        consistency_results = self.claim_consistency.compare(
            ClaimFacts(
                claimant_name=claim.claimant_name,
                vehicle_make=claim.vehicle_make,
                license_plate=claim.license_plate,
            ),
            validated_fields,
        )
        self.analysis_runs.save_consistency_checks(
            run, validation_records, consistency_results
        )

    def _process_document_ocr_category(
        self, run: WorkflowAnalysisRun, category: EvidenceCategory, evidence_items: list[Evidence]
    ) -> list[DocumentOcrResult]:
        ocr_records = [
            (item, self.analysis_runs.create_document_ocr_result(run, item))
            for item in evidence_items
        ]
        warnings: list[str] = []
        statuses: list[AnalysisResultStatus] = []

        for evidence, record in ocr_records:
            reusable = self.analysis_runs.latest_document_ocr_for_evidence(
                evidence.id, run.id
            )
            if reusable is not None:
                self.analysis_runs.copy_document_ocr_result(record, reusable)
                if reusable.warning:
                    warnings.append(f"{evidence.original_filename}: {reusable.warning}")
                statuses.append(reusable.status)
                continue
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
                    adapter_metadata={**extracted.metadata, "ocr_reused": False},
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
        return [record for _, record in ocr_records]

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
            raise LookupError("Document field validation not found")
        if self.workflow_ai_reviews.find_for_run(run_id):
            raise ValueError("Re-run analysis before changing fields after AI review")

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
            raise LookupError("Document extracted field not found")
        if self.workflow_ai_reviews.find_for_run(run_id):
            raise ValueError("Re-run analysis before changing fields after AI review")
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
        if self.workflow_ai_reviews.find_for_run(run_id):
            raise ValueError("Re-run analysis before changing fields after AI review")
        run = self.analysis_runs.find(run_id)
        if run is None or run.claim_id != claim.id:
            raise LookupError("Analysis run not found")
        field_ids = [item.id for item in request.fields]
        fields = self.analysis_runs.find_extracted_fields_for_claim(
            claim.id, run_id, field_ids
        )
        if len(fields) != len(field_ids):
            raise LookupError("One or more document extracted fields were not found")
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
        reasons = self._analysis_blocked_reasons(claim, run, values_by_id)
        if reasons:
            raise AnalysisConfirmationBlockedError(reasons)
        payload = self._build_analysis_snapshot_payload(claim, run, values_by_id)
        self.analysis_snapshots.save_ready(run, all_fields, values_by_id, payload)
        return self._to_response(claim)

    def _analysis_blocked_reasons(
        self,
        claim: Claim,
        run: WorkflowAnalysisRun,
        values_by_id: dict[int, str],
    ) -> list[AnalysisBlockedReasonResponse]:
        reasons: list[AnalysisBlockedReasonResponse] = []
        incident = self.claim_incidents.find_for_claim(claim.id)
        if incident is None or incident.input_revision != run.input_revision:
            reasons.append(
                AnalysisBlockedReasonResponse(
                    code="INPUTS_CHANGED",
                    message="Claim information or evidence changed; run analysis again.",
                )
            )
        damage = self.analysis_runs.damage_analysis(run.id)
        if run.damage_status is not AnalysisResultStatus.COMPLETED or damage is None:
            reasons.append(
                AnalysisBlockedReasonResponse(
                    code="DAMAGE_ANALYSIS_UNAVAILABLE",
                    message="Vehicle damage analysis must complete before Save All.",
                )
            )

        documents = {
            item.document_type: item
            for item in self.analysis_runs.documents(run.id)
        }
        fields_by_category = self._extracted_fields_by_category(run.id)
        claim_facts = ClaimFacts(
            claimant_name=claim.claimant_name,
            vehicle_make=claim.vehicle_make,
            license_plate=claim.license_plate,
        )
        for category in DOCUMENT_EVIDENCE_CATEGORIES:
            document = documents.get(category)
            category_fields = fields_by_category.get(category, [])
            if document is None:
                reasons.append(
                    AnalysisBlockedReasonResponse(
                        code="DOCUMENT_CATEGORY_MISSING",
                        category=category,
                        message=f"{category.value} analysis is missing.",
                    )
                )
                continue
            if document.status is not AnalysisResultStatus.COMPLETED or not category_fields:
                reasons.append(
                    AnalysisBlockedReasonResponse(
                        code="DOCUMENT_CATEGORY_FAILED",
                        category=category,
                        message=f"{category.value} analysis is incomplete or failed.",
                    )
                )
                continue
            for field in category_fields:
                proposed_value = values_by_id.get(field.id, "").strip()
                if not proposed_value:
                    reasons.append(
                        AnalysisBlockedReasonResponse(
                            code="REQUIRED_VALUE_MISSING",
                            category=category,
                            field_id=field.id,
                            field_key=field.field_key,
                            message=f"{field.field_key} requires a confirmed value.",
                        )
                    )
                    continue
                comparison = self.claim_consistency.compare_value(
                    claim_facts,
                    field.field_key,
                    field.source_evidence_id,
                    proposed_value,
                )
                if (
                    comparison is not None
                    and comparison.status is not ConsistencyStatus.MATCH
                ):
                    reasons.append(
                        AnalysisBlockedReasonResponse(
                            code=(
                                "COMPARISON_MISMATCH"
                                if comparison.status is ConsistencyStatus.MISMATCH
                                else "COMPARISON_UNAVAILABLE"
                            ),
                            category=category,
                            field_id=field.id,
                            field_key=field.field_key,
                            message=comparison.explanation,
                        )
                    )
        return reasons

    def _extracted_fields_by_category(
        self, run_id: int
    ) -> dict[EvidenceCategory, list[DocumentExtractedField]]:
        fields_by_category: dict[EvidenceCategory, list[DocumentExtractedField]] = {}
        for ocr_result in self.analysis_runs.document_ocr_results(run_id):
            extraction = self.analysis_runs.document_extraction_for_ocr(ocr_result.id)
            if extraction is None:
                continue
            fields_by_category.setdefault(ocr_result.document_type, []).extend(
                self.analysis_runs.extracted_fields_for_result(extraction.id)
            )
        return fields_by_category

    def _build_analysis_snapshot_payload(
        self,
        claim: Claim,
        run: WorkflowAnalysisRun,
        values_by_id: dict[int, str],
    ) -> dict[str, object]:
        claim_facts = ClaimFacts(
            claimant_name=claim.claimant_name,
            vehicle_make=claim.vehicle_make,
            license_plate=claim.license_plate,
        )
        fields_by_category = self._extracted_fields_by_category(run.id)
        documents_by_category = {
            item.document_type: item for item in self.analysis_runs.documents(run.id)
        }
        ocr_results = self.analysis_runs.document_ocr_results(run.id)
        documents: list[dict[str, object]] = []
        warnings: list[str] = []
        for category in DOCUMENT_EVIDENCE_CATEGORIES:
            document = documents_by_category[category]
            document_warnings = json.loads(document.warnings_json)
            warnings.extend(document_warnings)
            documents.append(
                {
                    "document_type": category.value,
                    "status": document.status.value,
                    "source_evidence_ids": [
                        result.evidence_id
                        for result in ocr_results
                        if result.document_type is category
                    ],
                    "confirmed_fields": [
                        {
                            "field_id": field.id,
                            "field_key": field.field_key,
                            "source_evidence_id": field.source_evidence_id,
                            "ai_extracted_value": field.ai_extracted_value,
                            "confirmed_value": values_by_id[field.id],
                            "comparison": (
                                comparison.model_dump(mode="json")
                                if (
                                    comparison := self._comparison_response(
                                        self.claim_consistency.compare_value(
                                            claim_facts,
                                            field.field_key,
                                            field.source_evidence_id,
                                            values_by_id[field.id],
                                        )
                                    )
                                )
                                else None
                            ),
                            "prompt_version": field.prompt_version,
                            "schema_version": field.schema_version,
                        }
                        for field in fields_by_category[category]
                    ],
                    "warnings": document_warnings,
                }
            )

        damage = self.analysis_runs.damage_analysis(run.id)
        if damage is None:
            raise ValueError("Damage analysis is required for an analysis snapshot")
        detections = self.damage_analyses.list_detections(damage.id)
        model_output = self.damage_analyses.model_output(damage.id)
        reference_prices = self.damage_analyses.reference_prices(damage.id)
        if damage.warning:
            warnings.append(damage.warning)
        if model_output is not None:
            warnings.extend(json.loads(model_output.warnings_json))
        evidence_references = [
            {
                "id": item.id,
                "category": item.category.value,
                "original_filename": item.original_filename,
            }
            for item in self.evidence.list_for_claim(claim.id)
        ]
        incident = self._incident_response(claim.id)
        return {
            "documents": documents,
            "damage": {
                "analysis_id": damage.analysis_number,
                "assessment": damage.assessment.value,
                "warning": damage.warning,
                "findings": [
                    {
                        "vehicle_part": item.vehicle_part,
                        "damage_type": item.damage_type,
                        "damage_percentage": item.damage_percentage,
                        "confidence": item.confidence,
                        "source_evidence_id": item.source_evidence_id,
                        "annotated_evidence_id": item.annotated_evidence_id,
                    }
                    for item in detections
                ],
                "model_output": json.loads(model_output.output_json) if model_output else None,
                "reference_prices": [
                    {
                        "part_identity": price.part_identity,
                        "amount": price.amount,
                        "currency": price.currency,
                        "source_name": price.source_name,
                        "source_url": price.source_url,
                        "price_type": price.price_type,
                        "status": price.status.value,
                    }
                    for price in reference_prices
                ],
            },
            "claim": {"id": claim.claim_number, "status": claim.status.value},
            "vehicle": {
                "make": claim.vehicle_make,
                "model": claim.vehicle_model,
                "year": claim.vehicle_year,
                "license_plate": claim.license_plate,
                "vin": claim.vin,
            },
            "claimant": {"name": claim.claimant_name},
            "incident": incident.model_dump(mode="json") if incident else None,
            "warnings": list(dict.fromkeys(warnings)),
            "evidence_references": evidence_references,
        }

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
        snapshot = self.analysis_snapshots.find_for_run(run.id)
        incident_record = self.claim_incidents.find_for_claim(claim.id)
        if snapshot is None:
            raise AnalysisConfirmationBlockedError(
                [
                    AnalysisBlockedReasonResponse(
                        code="SNAPSHOT_MISSING",
                        message="Save All is required before AI Review.",
                    )
                ]
            )
        if (
            snapshot.status is AnalysisSnapshotStatus.STALE
            or incident_record is None
            or snapshot.input_revision != incident_record.input_revision
        ):
            raise AnalysisConfirmationBlockedError(
                [
                    AnalysisBlockedReasonResponse(
                        code="SNAPSHOT_STALE",
                        message="Confirmed analysis is stale; save the corrected analysis again.",
                    )
                ]
            )
        damage = self.analysis_runs.damage_analysis(run.id)
        if damage is None:
            raise AnalysisConfirmationBlockedError(
                [
                    AnalysisBlockedReasonResponse(
                        code="DAMAGE_ANALYSIS_UNAVAILABLE",
                        message="Damage analysis is required before AI Review.",
                    )
                ]
            )

        payload = json.loads(snapshot.payload_json)
        warnings = payload.get("warnings", [])
        evidence_references = payload.get("evidence_references", [])
        input_data = self._copilot_input_from_snapshot(payload)
        result = self.llm_copilot.generate(input_data)
        provider_model = self.llm_model if result.status is CopilotConclusionStatus.GENERATED else None
        conclusion = self.copilot_conclusions.create(damage, result, provider_model)
        failed_documents = sum(
            document["status"] == AnalysisResultStatus.FAILED.value
            for document in payload.get("documents", [])
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
            raise ValueError("Upload at least one vehicle damage image before running analysis")
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
        if claim.claim_number is None:
            raise ValueError("Claim number must be assigned before serialization")

        evidence_groups = self.evidence.group_details_for_claim(claim.id)
        terminal_run = self.analysis_runs.latest_terminal_for_claim(claim.id)
        analyzed_evidence_ids = (
            {
                result.evidence_id
                for result in self.analysis_runs.document_ocr_results(terminal_run.id)
            }
            if terminal_run
            else set()
        )
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
                self._to_evidence_response(
                    claim.claim_number,
                    item,
                    evidence_groups.get(item.id),
                    analysis_required=(
                        item.category in DOCUMENT_EVIDENCE_CATEGORIES
                        and item.id not in analyzed_evidence_ids
                    ),
                )
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
        claim = self.claims.find_by_id(run.claim_id)
        if claim is None:
            raise ValueError("Analysis run claim must be available")
        claim_facts = ClaimFacts(
            claimant_name=claim.claimant_name,
            vehicle_make=claim.vehicle_make,
            license_plate=claim.license_plate,
        )
        analysis_readiness, analysis_snapshot = self._analysis_snapshot_state(
            claim, run
        )
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
                    adapter_metadata=self._public_adapter_metadata(
                        result.adapter_metadata_json
                    ),
                    warning=result.warning,
                    created_at=result.created_at,
                    processed_at=result.processed_at,
                    reused=bool(
                        json.loads(result.adapter_metadata_json).get("ocr_reused", False)
                    ),
                    extraction=self._document_extraction_response(
                        result.id,
                        claim_facts,
                        json.loads(result.adapter_metadata_json),
                    ),
                    field_validations=[
                        DocumentFieldValidationResponse(
                            id=validation.id,
                            analysis_run_id=validation.analysis_run_id,
                            document_ocr_result_id=validation.document_ocr_result_id,
                            source_evidence_id=validation.source_evidence_id,
                            field_key=validation.field_key,
                            prompt_version=validation.prompt_version,
                            ocr_value=validation.ocr_value,
                            normalized_value=validation.normalized_value,
                            status=validation.status,
                            confidence=validation.confidence,
                            summary=validation.summary,
                            warnings=json.loads(validation.warnings_json),
                        )
                        for validation in self.analysis_runs.field_validations_for_ocr(
                            result.id
                        )
                    ],
                )
                for result in self.analysis_runs.document_ocr_results(run.id)
            ],
            consistency_checks=[
                ClaimConsistencyCheckResponse(
                    id=check.id,
                    field_validation_id=check.field_validation_id,
                    source_evidence_id=check.source_evidence_id,
                    field_key=check.field_key,
                    claim_value=check.claim_value,
                    document_value=check.document_value,
                    status=check.status,
                    explanation=check.explanation,
                )
                for check in self.analysis_runs.consistency_checks(run.id)
            ],
            analysis_readiness=analysis_readiness,
            analysis_snapshot=analysis_snapshot,
            failure_reason=run.failure_reason,
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
            inputs_changed=incident is None or incident.input_revision != run.input_revision,
        )

    def _analysis_snapshot_state(
        self, claim: Claim, run: WorkflowAnalysisRun
    ) -> tuple[AnalysisReadinessResponse, ConfirmedAnalysisSnapshotResponse | None]:
        snapshot = self.analysis_snapshots.find_for_run(run.id)
        incident = self.claim_incidents.find_for_claim(claim.id)
        if snapshot is not None:
            payload = json.loads(snapshot.payload_json)
            stale = (
                snapshot.status is AnalysisSnapshotStatus.STALE
                or incident is None
                or snapshot.input_revision != incident.input_revision
            )
            status = "STALE" if stale else "READY"
            reasons = (
                [
                    AnalysisBlockedReasonResponse(
                        code="SNAPSHOT_STALE",
                        message="Confirmed analysis is stale; save the corrected analysis again.",
                    )
                ]
                if stale
                else []
            )
            return (
                AnalysisReadinessResponse(status=status, blocked_reasons=reasons),
                ConfirmedAnalysisSnapshotResponse(
                    status=status,
                    documents=payload.get("documents", []),
                    damage=payload.get("damage", {}),
                    warnings=payload.get("warnings", []),
                    evidence_references=payload.get("evidence_references", []),
                    saved_at=snapshot.updated_at,
                ),
            )

        current_values = {
            field.id: (field.confirmed_value or "")
            for field in self.analysis_runs.extracted_fields(run.id)
        }
        reasons = self._analysis_blocked_reasons(claim, run, current_values)
        missing_snapshot = AnalysisBlockedReasonResponse(
            code="SNAPSHOT_MISSING",
            message="Save All is required before AI Review.",
        )
        return (
            AnalysisReadinessResponse(
                status="BLOCKED" if reasons else "NOT_SAVED",
                blocked_reasons=[missing_snapshot, *reasons],
            ),
            None,
        )

    def _document_extraction_response(
        self,
        document_ocr_result_id: int,
        claim_facts: ClaimFacts,
        ocr_metadata: dict[str, object] | None = None,
    ) -> DocumentExtractionResultResponse | None:
        extraction = self.analysis_runs.document_extraction_for_ocr(document_ocr_result_id)
        if extraction is None:
            return None
        return DocumentExtractionResultResponse(
            id=extraction.id,
            analysis_run_id=extraction.analysis_run_id,
            document_ocr_result_id=extraction.document_ocr_result_id,
            source_evidence_id=extraction.source_evidence_id,
            document_type=extraction.document_type,
            status=extraction.status,
            prompt_version=extraction.prompt_version,
            schema_version=extraction.schema_version,
            warning=extraction.warning,
            created_at=extraction.created_at,
            processed_at=extraction.processed_at,
            reused=bool((ocr_metadata or {}).get("extraction_reused", False)),
            fields=[
                DocumentExtractedFieldResponse(
                    id=field.id,
                    analysis_run_id=field.analysis_run_id,
                    extraction_result_id=field.extraction_result_id,
                    source_evidence_id=field.source_evidence_id,
                    field_key=field.field_key,
                    ai_extracted_value=field.ai_extracted_value,
                    confirmed_value=field.confirmed_value,
                    prompt_version=field.prompt_version,
                    schema_version=field.schema_version,
                    created_at=field.created_at,
                    updated_at=field.updated_at,
                    comparison=self._comparison_response(
                        self.claim_consistency.compare_value(
                            claim_facts,
                            field.field_key,
                            field.source_evidence_id,
                            field.confirmed_value,
                        )
                    ),
                )
                for field in self.analysis_runs.extracted_fields_for_result(extraction.id)
            ],
        )

    def _confirmed_fields_by_category(
        self,
        ocr_results: list[DocumentOcrResult],
        claim_facts: ClaimFacts,
    ) -> dict[EvidenceCategory, list[dict[str, object]]]:
        fields_by_category: dict[EvidenceCategory, list[dict[str, object]]] = {}
        for ocr_result in ocr_results:
            extraction = self.analysis_runs.document_extraction_for_ocr(ocr_result.id)
            if extraction is None:
                continue
            category_fields: list[dict[str, object]] = []
            for field in self.analysis_runs.extracted_fields_for_result(extraction.id):
                comparison = self._comparison_response(
                    self.claim_consistency.compare_value(
                        claim_facts,
                        field.field_key,
                        field.source_evidence_id,
                        field.confirmed_value,
                    )
                )
                category_fields.append(
                    {
                        "field_key": field.field_key,
                        "source_evidence_id": field.source_evidence_id,
                        "ai_extracted_value": field.ai_extracted_value,
                        "confirmed_value": field.confirmed_value,
                        "comparison": (
                            comparison.model_dump(mode="json") if comparison else None
                        ),
                    }
                )
            fields_by_category[ocr_result.document_type] = category_fields
        return fields_by_category

    @staticmethod
    def _comparison_response(
        result: ConsistencyResult | None,
    ) -> DocumentFieldComparisonResponse | None:
        if result is None:
            return None
        return DocumentFieldComparisonResponse(
            claim_value=result.claim_value,
            document_value=result.document_value,
            status=result.status,
            explanation=result.explanation,
        )

    @staticmethod
    def _public_adapter_metadata(metadata_json: str) -> dict[str, object]:
        metadata = json.loads(metadata_json)
        return {
            key: value
            for key, value in metadata.items()
            if key
            not in {
                "ocr_reused",
                "ocr_reused_from_analysis_run_id",
                "extraction_reused",
                "extraction_reused_from_analysis_run_id",
            }
        }

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
        model_output = self.damage_analyses.model_output(analysis.id)
        model_output_response = None
        if model_output is not None:
            output_payload = json.loads(model_output.output_json)
            model_output_response = {
                "adapter_name": model_output.adapter_name,
                "part_identities": output_payload.get("part_identities", []),
                "record": output_payload["record"],
                "warnings": json.loads(model_output.warnings_json),
            }
        return DamageAnalysisResponse(
            id=analysis.analysis_number,
            assessment=analysis.assessment,
            warning=analysis.warning,
            detections=detections,
            model_output=model_output_response,
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
    def _copilot_input_from_snapshot(payload: dict[str, object]) -> CopilotInput:
        claim_payload = payload["claim"]
        claimant_payload = payload["claimant"]
        vehicle_payload = payload["vehicle"]
        incident_payload = payload.get("incident")
        damage_payload = payload["damage"]
        documents: dict[str, AiReviewDocument] = {}
        for document in payload.get("documents", []):
            fields: dict[str, AiReviewDocumentField] = {}
            for field in document.get("confirmed_fields", []):
                comparison = field.get("comparison") or {}
                fields[field["field_key"]] = AiReviewDocumentField(
                    value=field.get("confirmed_value"),
                    consistency=comparison.get("status"),
                )
            documents[document["document_type"]] = AiReviewDocument(fields=fields)

        return CopilotInput(
            context=AiReviewContext(
                claim=AiReviewClaimFacts(
                    claim_number=claim_payload["id"],
                    status=claim_payload["status"],
                    claimant_name=claimant_payload["name"],
                ),
                vehicle=AiReviewVehicleFacts(
                    make=vehicle_payload["make"],
                    model=vehicle_payload["model"],
                    year=vehicle_payload["year"],
                    license_plate=vehicle_payload.get("license_plate"),
                    vin=vehicle_payload.get("vin"),
                ),
                incident=(
                    AiReviewIncidentFacts(
                        occurred_at=incident_payload.get("occurred_at"),
                        location=incident_payload.get("location"),
                        description=incident_payload.get("description"),
                    )
                    if incident_payload
                    else None
                ),
                documents=documents,
                damage=AiReviewDamage(
                    assessment=damage_payload["assessment"],
                    warning=damage_payload.get("warning"),
                    findings=[
                        AiReviewDamageFinding(
                            part=item.get("vehicle_part"),
                            damage_type=item.get("damage_type"),
                            area_percentage=item["damage_percentage"],
                        )
                        for item in damage_payload.get("findings", [])
                    ],
                ),
                warnings=payload.get("warnings", []),
                reference_prices=[
                    AiReviewReferencePrice(
                        part=price["part_identity"],
                        amount=price.get("amount"),
                        currency=price.get("currency"),
                        source_name=price.get("source_name"),
                        price_type=price["price_type"],
                        status=price["status"],
                    )
                    for price in damage_payload.get("reference_prices", [])
                ],
            )
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
        review_output = self.copilot_conclusions.review_output(conclusion.id)
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
            structured_review=(
                AiReviewStructuredResponse.model_validate(
                    json.loads(review_output.review_json)
                )
                if review_output
                else None
            ),
            prompt_version=review_output.prompt_version if review_output else None,
            schema_version=review_output.schema_version if review_output else None,
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
        analysis_required: bool = False,
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
            analysis_required=analysis_required,
        )
