import json

from app.models import AnalysisResultStatus, AnalysisRunStatus, AnalysisSnapshotStatus, Claim, ClaimStatus, CopilotConclusionStatus, User
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.repositories.claims import ClaimRepository
from app.repositories.claim_incidents import ClaimIncidentRepository
from app.repositories.damage_analyses import DamageAnalysisRepository
from app.repositories.copilot_conclusions import CopilotConclusionRepository
from app.repositories.copilot_conclusion_reviews import CopilotConclusionAlreadyReviewedError, CopilotConclusionReviewRepository
from app.repositories.workflow_ai_reviews import WorkflowAiReviewRepository
from app.schemas.claims import AnalysisBlockedReasonResponse, CopilotConclusionReviewRequest, CopilotConclusionReviewRevertRequest
from app.services.analysis_errors import AnalysisConfirmationBlockedError
from app.services.claim_errors import ClaimConflictError, ClaimResourceNotFoundError, ClaimValidationError
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


class ClaimReviewOperations:
    def __init__(
        self,
        claims: ClaimRepository,
        analysis_runs: AnalysisRunRepository,
        analysis_snapshots: AnalysisSnapshotRepository,
        claim_incidents: ClaimIncidentRepository,
        damage_analyses: DamageAnalysisRepository,
        workflow_ai_reviews: WorkflowAiReviewRepository,
        copilot_conclusions: CopilotConclusionRepository,
        copilot_conclusion_reviews: CopilotConclusionReviewRepository,
        llm_copilot: LlmCopilotService,
        llm_model: str | None,
    ) -> None:
        self.claims = claims
        self.analysis_runs = analysis_runs
        self.analysis_snapshots = analysis_snapshots
        self.claim_incidents = claim_incidents
        self.damage_analyses = damage_analyses
        self.workflow_ai_reviews = workflow_ai_reviews
        self.copilot_conclusions = copilot_conclusions
        self.copilot_conclusion_reviews = copilot_conclusion_reviews
        self.llm_copilot = llm_copilot
        self.llm_model = llm_model

    def run_workflow_ai_review(self, claim_number: str, run_id: int) -> Claim | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        run = self.analysis_runs.find(run_id)
        if run is None or run.claim_id != claim.id:
            raise ClaimResourceNotFoundError("Analysis run not found")
        if run.status not in {AnalysisRunStatus.COMPLETED, AnalysisRunStatus.PARTIAL}:
            raise ClaimValidationError("Analysis results are not ready for AI review")
        if self.workflow_ai_reviews.find_for_run(run.id):
            raise ClaimConflictError("AI review has already been generated for this analysis")
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
        return claim

    def review_copilot_conclusion(
        self,
        claim_number: str,
        conclusion_id: int,
        request: CopilotConclusionReviewRequest,
        reviewer: User,
    ) -> Claim | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        conclusion = self.copilot_conclusions.find_for_claim(claim.id, conclusion_id)
        if conclusion is None:
            raise ClaimResourceNotFoundError("AI conclusion not found")
        if self.copilot_conclusion_reviews.exists_for_conclusion(conclusion.id):
            raise ClaimConflictError("AI conclusion has already been reviewed")
        if claim.status is not ClaimStatus.REVIEW_REQUIRED:
            raise ClaimValidationError("Claim is not awaiting AI conclusion review")
        latest_analysis = self.damage_analyses.latest_for_claim(claim.id)
        if latest_analysis is None or conclusion.analysis_id != latest_analysis.id:
            raise ClaimValidationError("AI conclusion is not current")
        try:
            self.copilot_conclusion_reviews.create(claim, conclusion, request, reviewer)
        except CopilotConclusionAlreadyReviewedError as error:
            raise ClaimConflictError("AI conclusion has already been reviewed") from error
        return claim

    def revert_copilot_conclusion_review(
        self,
        claim_number: str,
        conclusion_id: int,
        request: CopilotConclusionReviewRevertRequest,
        reviewer: User,
    ) -> Claim | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        review = self.copilot_conclusion_reviews.find_for_conclusion(conclusion_id)
        if review is None or review.claim_id != claim.id:
            raise ClaimResourceNotFoundError("AI conclusion review not found")
        if self.copilot_conclusion_reviews.reversion_for_review(review.id):
            raise ClaimConflictError("AI conclusion review has already been reverted")
        self.copilot_conclusion_reviews.revert(claim, review, reviewer, request.note)
        return claim

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
