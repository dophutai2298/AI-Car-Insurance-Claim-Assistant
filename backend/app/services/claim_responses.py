from __future__ import annotations

import json

from app.models import (
    Claim, CopilotConclusion, CopilotConclusionReview, DamageAnalysis,
    DocumentOcrResult, Evidence, EvidenceCategory, ReferencePartPrice, ReferencePriceLookupStatus,
    ReferencePriceStatus, WorkflowAnalysisRun,
)
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.claims import ClaimRepository
from app.repositories.claim_incidents import ClaimIncidentRepository
from app.repositories.damage_analyses import DamageAnalysisRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.copilot_conclusions import CopilotConclusionRepository
from app.repositories.copilot_conclusion_reviews import CopilotConclusionReviewRepository
from app.repositories.workflow_ai_reviews import WorkflowAiReviewRepository
from app.services.analysis_snapshots import AnalysisSnapshotOperations
from app.schemas.claims import (
    ClaimResponse,
    VehicleMetadata, EvidenceResponse, EvidenceReferenceResponse, WorkflowAnalysisRunResponse,
    DocumentAnalysisResponse, DocumentAnalysisFieldResponse,
    DocumentOcrResultResponse, DocumentFieldValidationResponse,
    DocumentExtractionResultResponse, DocumentExtractedFieldResponse,
    ClaimConsistencyCheckResponse,
    DamageAnalysisResponse, DamageDetectionResponse, ReferencePartPriceResponse,
    CopilotConclusionResponse, CopilotConclusionReviewResponse,
    CopilotFindingResponse, AiReviewStructuredResponse,
)
from app.schemas.admin import AssessmentRuleValuesSchema
from app.services.document_consistency import ClaimConsistencyService, ClaimFacts

DOCUMENT_EVIDENCE_CATEGORIES = (
    EvidenceCategory.ID_CARD,
    EvidenceCategory.INSURANCE_POLICY,
    EvidenceCategory.VEHICLE_REGISTRATION,
    EvidenceCategory.DRIVER_LICENSE,
)


class ClaimResponseAssembler:
    def __init__(
        self,
        claims: ClaimRepository,
        claim_incidents: ClaimIncidentRepository,
        evidence: EvidenceRepository,
        damage_analyses: DamageAnalysisRepository,
        copilot_conclusions: CopilotConclusionRepository,
        copilot_conclusion_reviews: CopilotConclusionReviewRepository,
        workflow_ai_reviews: WorkflowAiReviewRepository,
        analysis_runs: AnalysisRunRepository,
        claim_consistency: ClaimConsistencyService,
        snapshots: AnalysisSnapshotOperations,
    ) -> None:
        self.claims = claims
        self.claim_incidents = claim_incidents
        self.evidence = evidence
        self.damage_analyses = damage_analyses
        self.copilot_conclusions = copilot_conclusions
        self.copilot_conclusion_reviews = copilot_conclusion_reviews
        self.workflow_ai_reviews = workflow_ai_reviews
        self.analysis_runs = analysis_runs
        self.claim_consistency = claim_consistency
        self.snapshots = snapshots

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
            incident=self.snapshots.incident_response(claim.id),
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
        analysis_readiness, analysis_snapshot = self.snapshots.state(
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
                    comparison=self.snapshots.comparison_response(
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
                comparison = self.snapshots.comparison_response(
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
