import logging

from app.models import AnalysisRunStatus, Claim, ClaimStatus, EvidenceCategory, WorkflowAnalysisRun
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.claims import ClaimRepository
from app.repositories.claim_incidents import ClaimIncidentRepository
from app.repositories.damage_analyses import DamageAnalysisRepository
from app.repositories.evidence import EvidenceRepository
from app.services.assessment_rules import AssessmentRuleService
from app.services.damage_assessment import DamageAssessmentService
from app.services.damage_model import DamageModelAdapter
from app.services.claim_errors import ClaimConflictError, ClaimValidationError
from app.services.document_pipeline import DocumentAnalysisPipeline
from app.services.part_search import PartSearchService

REQUIRED_EVIDENCE_CATEGORIES = (
    EvidenceCategory.VEHICLE_DAMAGE_IMAGE,
    EvidenceCategory.ID_CARD,
    EvidenceCategory.INSURANCE_POLICY,
    EvidenceCategory.VEHICLE_REGISTRATION,
    EvidenceCategory.DRIVER_LICENSE,
)
logger = logging.getLogger(__name__)


class WorkflowAnalysisOperations:
    def __init__(
        self,
        claims: ClaimRepository,
        claim_incidents: ClaimIncidentRepository,
        evidence: EvidenceRepository,
        analysis_runs: AnalysisRunRepository,
        damage_analyses: DamageAnalysisRepository,
        damage_model: DamageModelAdapter,
        assessment: DamageAssessmentService,
        rules: AssessmentRuleService,
        part_search: PartSearchService,
        document_pipeline: DocumentAnalysisPipeline,
    ) -> None:
        self.claims = claims
        self.claim_incidents = claim_incidents
        self.evidence = evidence
        self.analysis_runs = analysis_runs
        self.damage_analyses = damage_analyses
        self.damage_model = damage_model
        self.assessment = assessment
        self.rules = rules
        self.part_search = part_search
        self.document_pipeline = document_pipeline

    def start_workflow_analysis(self, claim_number: str) -> WorkflowAnalysisRun | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        if claim.status in {ClaimStatus.AI_APPROVED, ClaimStatus.AI_REJECTED}:
            raise ClaimValidationError("Revert the human review before running analysis again")
        active_run = self.analysis_runs.latest_for_claim(claim.id)
        if active_run and active_run.status in {AnalysisRunStatus.PENDING, AnalysisRunStatus.PROCESSING}:
            raise ClaimConflictError("Analysis is already running")
        incident = self.claim_incidents.find_for_claim(claim.id)
        if incident is None:
            raise ClaimValidationError("Complete incident information before starting analysis")
        evidence = self.evidence.list_for_claim(claim.id)
        uploaded_categories = {item.category for item in evidence}
        missing = [category.value for category in REQUIRED_EVIDENCE_CATEGORIES if category not in uploaded_categories]
        if missing:
            raise ClaimValidationError(f"Upload required evidence before starting analysis: {', '.join(missing)}")
        run = self.analysis_runs.create(claim, incident.input_revision)
        return run

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
        except Exception:
            logger.exception("Workflow analysis failed for run %s", run_id)
            self.claims.session.rollback()
            self.analysis_runs.fail(run, claim, "Analysis processing failed")

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
        except Exception:
            logger.exception("Damage analysis failed for run %s", run.id)
            self.analysis_runs.mark_damage_failed(run, "Damage analysis failed")

        previous_run = self.analysis_runs.latest_before(claim.id, run.id)
        self.document_pipeline.process(run, previous_run, claim, by_category)

        self.analysis_runs.complete(run, claim)
