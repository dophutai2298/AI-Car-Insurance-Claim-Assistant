import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Claim, CopilotConclusion, CopilotReviewOutput, DamageAnalysis
from app.services.llm_copilot import CopilotConclusionResult


class CopilotConclusionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        analysis: DamageAnalysis,
        conclusion: CopilotConclusionResult,
        provider_model: str | None,
    ) -> CopilotConclusion:
        record = CopilotConclusion(
            analysis_id=analysis.id,
            status=conclusion.status,
            recommendation=conclusion.recommendation,
            summary=conclusion.summary,
            fallback_summary=conclusion.fallback_summary,
            failure_reason=conclusion.failure_reason,
            provider_model=provider_model,
        )
        self.session.add(record)
        self.session.flush()
        self.session.add(
            CopilotReviewOutput(
                conclusion_id=record.id,
                review_json=json.dumps(
                    conclusion.structured_review.model_dump(mode="json"),
                    ensure_ascii=False,
                ),
                prompt_version=conclusion.prompt_version,
                schema_version=conclusion.schema_version,
            )
        )
        self.session.commit()
        self.session.refresh(record)
        return record

    def find_for_analysis(self, analysis_id: int) -> CopilotConclusion | None:
        statement = select(CopilotConclusion).where(CopilotConclusion.analysis_id == analysis_id)
        return self.session.scalar(statement)

    def find_for_claim(self, claim_id: int, conclusion_id: int) -> CopilotConclusion | None:
        statement = (
            select(CopilotConclusion)
            .join(DamageAnalysis, DamageAnalysis.id == CopilotConclusion.analysis_id)
            .join(Claim, Claim.id == DamageAnalysis.claim_id)
            .where(Claim.id == claim_id, CopilotConclusion.id == conclusion_id)
        )
        return self.session.scalar(statement)

    def review_output(self, conclusion_id: int) -> CopilotReviewOutput | None:
        return self.session.scalar(
            select(CopilotReviewOutput).where(
                CopilotReviewOutput.conclusion_id == conclusion_id
            )
        )
