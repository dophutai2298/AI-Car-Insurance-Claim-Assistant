from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Claim,
    ClaimConsistencyCheck,
    ClaimIncident,
    ConfirmedAnalysisSnapshot,
    CopilotConclusion,
    CopilotConclusionReview,
    CopilotConclusionReviewReversion,
    CopilotReviewOutput,
    CopilotReviewTranslation,
    DamageAnalysis,
    DamageAnalysisRuleSnapshot,
    DamageDetection,
    DamageModelOutput,
    DocumentAnalysis,
    DocumentAnalysisField,
    DocumentExtractedField,
    DocumentExtractionResult,
    DocumentFieldValidation,
    DocumentOcrResult,
    Evidence,
    EvidenceRemoval,
    OtherDocumentGroup,
    OtherDocumentGroupEvidence,
    ReferencePartPrice,
    WorkflowAiReview,
    WorkflowAnalysisDamage,
    WorkflowAnalysisRun,
)


class ClaimDeletionRepository:
    """Deletes a claim's dependent records in foreign-key-safe order."""

    def __init__(self, session: Session):
        self.session = session

    def delete_claim_graph(self, claim: Claim) -> None:
        claim_id = claim.id
        run_ids = select(WorkflowAnalysisRun.id).where(
            WorkflowAnalysisRun.claim_id == claim_id
        ).scalar_subquery()
        damage_ids = select(DamageAnalysis.id).where(
            DamageAnalysis.claim_id == claim_id
        ).scalar_subquery()
        conclusion_ids = select(CopilotConclusion.id).where(
            CopilotConclusion.analysis_id.in_(damage_ids)
        ).scalar_subquery()
        review_ids = select(CopilotConclusionReview.id).where(
            CopilotConclusionReview.claim_id == claim_id
        ).scalar_subquery()
        ocr_ids = select(DocumentOcrResult.id).where(
            DocumentOcrResult.analysis_run_id.in_(run_ids)
        ).scalar_subquery()
        extraction_ids = select(DocumentExtractionResult.id).where(
            DocumentExtractionResult.analysis_run_id.in_(run_ids)
        ).scalar_subquery()
        document_analysis_ids = select(DocumentAnalysis.id).where(
            DocumentAnalysis.analysis_run_id.in_(run_ids)
        ).scalar_subquery()
        field_validation_ids = select(DocumentFieldValidation.id).where(
            DocumentFieldValidation.analysis_run_id.in_(run_ids)
        ).scalar_subquery()
        evidence_ids = select(Evidence.id).where(Evidence.claim_id == claim_id).scalar_subquery()
        other_group_ids = select(OtherDocumentGroup.id).where(
            OtherDocumentGroup.claim_id == claim_id
        ).scalar_subquery()

        self.session.execute(
            delete(CopilotConclusionReviewReversion).where(
                CopilotConclusionReviewReversion.review_id.in_(review_ids)
            )
        )
        self.session.execute(
            delete(CopilotReviewTranslation).where(
                CopilotReviewTranslation.conclusion_id.in_(conclusion_ids)
            )
        )
        self.session.execute(
            delete(CopilotReviewOutput).where(
                CopilotReviewOutput.conclusion_id.in_(conclusion_ids)
            )
        )
        self.session.execute(
            delete(WorkflowAiReview).where(
                WorkflowAiReview.analysis_run_id.in_(run_ids)
            )
        )
        self.session.execute(
            delete(CopilotConclusionReview).where(
                CopilotConclusionReview.claim_id == claim_id
            )
        )
        self.session.execute(
            delete(CopilotConclusion).where(CopilotConclusion.analysis_id.in_(damage_ids))
        )
        self.session.execute(
            delete(DamageDetection).where(DamageDetection.analysis_id.in_(damage_ids))
        )
        self.session.execute(
            delete(DamageModelOutput).where(DamageModelOutput.analysis_id.in_(damage_ids))
        )
        self.session.execute(
            delete(DamageAnalysisRuleSnapshot).where(
                DamageAnalysisRuleSnapshot.analysis_id.in_(damage_ids)
            )
        )
        self.session.execute(
            delete(ReferencePartPrice).where(ReferencePartPrice.analysis_id.in_(damage_ids))
        )
        self.session.execute(
            delete(WorkflowAnalysisDamage).where(
                WorkflowAnalysisDamage.analysis_run_id.in_(run_ids)
            )
        )
        self.session.execute(delete(DamageAnalysis).where(DamageAnalysis.claim_id == claim_id))

        self.session.execute(
            delete(ClaimConsistencyCheck).where(
                ClaimConsistencyCheck.analysis_run_id.in_(run_ids)
            )
        )
        self.session.execute(
            delete(DocumentExtractedField).where(
                DocumentExtractedField.analysis_run_id.in_(run_ids)
            )
        )
        self.session.execute(
            delete(DocumentExtractionResult).where(
                DocumentExtractionResult.id.in_(extraction_ids)
            )
        )
        self.session.execute(
            delete(DocumentFieldValidation).where(
                DocumentFieldValidation.id.in_(field_validation_ids)
            )
        )
        self.session.execute(delete(DocumentOcrResult).where(DocumentOcrResult.id.in_(ocr_ids)))
        self.session.execute(
            delete(DocumentAnalysisField).where(
                DocumentAnalysisField.document_analysis_id.in_(document_analysis_ids)
            )
        )
        self.session.execute(
            delete(DocumentAnalysis).where(DocumentAnalysis.id.in_(document_analysis_ids))
        )
        self.session.execute(
            delete(ConfirmedAnalysisSnapshot).where(
                ConfirmedAnalysisSnapshot.analysis_run_id.in_(run_ids)
            )
        )
        self.session.execute(
            delete(WorkflowAnalysisRun).where(WorkflowAnalysisRun.claim_id == claim_id)
        )

        self.session.execute(
            delete(OtherDocumentGroupEvidence).where(
                OtherDocumentGroupEvidence.group_id.in_(other_group_ids)
            )
        )
        self.session.execute(
            delete(EvidenceRemoval).where(EvidenceRemoval.evidence_id.in_(evidence_ids))
        )
        self.session.execute(delete(OtherDocumentGroup).where(OtherDocumentGroup.claim_id == claim_id))
        self.session.execute(delete(Evidence).where(Evidence.claim_id == claim_id))
        self.session.execute(delete(ClaimIncident).where(ClaimIncident.claim_id == claim_id))
        self.session.execute(delete(Claim).where(Claim.id == claim_id))
