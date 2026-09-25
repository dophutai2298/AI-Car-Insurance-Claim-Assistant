import json
from datetime import timezone

from app.models import AnalysisResultStatus, AnalysisSnapshotStatus, Claim, ConsistencyStatus, DocumentExtractedField, EvidenceCategory, WorkflowAnalysisRun
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.repositories.claim_incidents import ClaimIncidentRepository
from app.repositories.damage_analyses import DamageAnalysisRepository
from app.repositories.evidence import EvidenceRepository
from app.schemas.claims import (
    AnalysisBlockedReasonResponse, AnalysisReadinessResponse,
    ConfirmedAnalysisSnapshotResponse, DocumentFieldComparisonResponse,
    IncidentInformation,
)
from app.services.document_consistency import ClaimConsistencyService, ClaimFacts, ConsistencyResult

DOCUMENT_EVIDENCE_CATEGORIES = (
    EvidenceCategory.ID_CARD,
    EvidenceCategory.INSURANCE_POLICY,
    EvidenceCategory.VEHICLE_REGISTRATION,
    EvidenceCategory.DRIVER_LICENSE,
)


class AnalysisSnapshotOperations:
    def __init__(
        self,
        analysis_runs: AnalysisRunRepository,
        analysis_snapshots: AnalysisSnapshotRepository,
        claim_incidents: ClaimIncidentRepository,
        damage_analyses: DamageAnalysisRepository,
        evidence: EvidenceRepository,
        claim_consistency: ClaimConsistencyService,
    ) -> None:
        self.analysis_runs = analysis_runs
        self.analysis_snapshots = analysis_snapshots
        self.claim_incidents = claim_incidents
        self.damage_analyses = damage_analyses
        self.evidence = evidence
        self.claim_consistency = claim_consistency

    @staticmethod
    def comparison_response(result: ConsistencyResult | None) -> DocumentFieldComparisonResponse | None:
        if result is None:
            return None
        return DocumentFieldComparisonResponse(
            claim_value=result.claim_value,
            document_value=result.document_value,
            status=result.status,
            explanation=result.explanation,
        )

    def incident_response(self, claim_id: int) -> IncidentInformation | None:
        incident = self.claim_incidents.find_for_claim(claim_id)
        if incident is None:
            return None
        occurred_at = incident.occurred_at
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        return IncidentInformation(
            occurred_at=occurred_at,
            location=incident.location,
            description=incident.description,
        )


    def blocked_reasons(
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

    def build_payload(
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
                                    comparison := self.comparison_response(
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
        incident = self.incident_response(claim.id)
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

    def state(
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
        reasons = self.blocked_reasons(claim, run, current_values)
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
