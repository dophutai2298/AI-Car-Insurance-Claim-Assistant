import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CopilotConclusion, WorkflowAiReview


class WorkflowAiReviewRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        analysis_run_id: int,
        conclusion: CopilotConclusion,
        validity_percentage: int,
        warnings: list[str],
        evidence_references: list[dict[str, object]],
    ) -> WorkflowAiReview:
        review = WorkflowAiReview(
            analysis_run_id=analysis_run_id,
            conclusion_id=conclusion.id,
            validity_percentage=validity_percentage,
            review_status="REVIEW_REQUIRED",
            warnings_json=json.dumps(warnings),
            evidence_references_json=json.dumps(evidence_references),
        )
        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)
        return review

    def find_for_run(self, analysis_run_id: int) -> WorkflowAiReview | None:
        return self.session.scalar(
            select(WorkflowAiReview).where(WorkflowAiReview.analysis_run_id == analysis_run_id)
        )

    def find_for_conclusion(self, conclusion_id: int) -> WorkflowAiReview | None:
        return self.session.scalar(
            select(WorkflowAiReview).where(WorkflowAiReview.conclusion_id == conclusion_id)
        )
