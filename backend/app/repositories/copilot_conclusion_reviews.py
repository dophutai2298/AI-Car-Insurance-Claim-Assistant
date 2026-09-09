from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Claim,
    ClaimStatus,
    CopilotConclusion,
    CopilotConclusionReview,
    CopilotConclusionReviewStatus,
    User,
)
from app.schemas.claims import CopilotConclusionReviewRequest


class CopilotConclusionAlreadyReviewedError(Exception):
    pass


class CopilotConclusionReviewRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        claim: Claim,
        conclusion: CopilotConclusion,
        request: CopilotConclusionReviewRequest,
        reviewer: User,
    ) -> CopilotConclusionReview:
        review = CopilotConclusionReview(
            claim_id=claim.id,
            conclusion_id=conclusion.id,
            status=request.status,
            reason_category=request.reason_category,
            comment=request.comment.strip() if request.comment else None,
            reviewer_user_id=reviewer.id,
        )
        claim.status = (
            ClaimStatus.AI_APPROVED
            if request.status is CopilotConclusionReviewStatus.APPROVED
            else ClaimStatus.AI_REJECTED
        )
        self.session.add(review)
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise CopilotConclusionAlreadyReviewedError from error
        self.session.refresh(review)
        return review

    def exists_for_conclusion(self, conclusion_id: int) -> bool:
        statement = select(CopilotConclusionReview.id).where(
            CopilotConclusionReview.conclusion_id == conclusion_id
        )
        return self.session.scalar(statement) is not None

    def list_for_conclusion(self, conclusion_id: int) -> list[tuple[CopilotConclusionReview, str]]:
        statement = (
            select(CopilotConclusionReview, User.email)
            .join(User, User.id == CopilotConclusionReview.reviewer_user_id)
            .where(CopilotConclusionReview.conclusion_id == conclusion_id)
            .order_by(CopilotConclusionReview.reviewed_at.desc())
        )
        return list(self.session.execute(statement).all())

    def list_for_claim(self, claim_id: int) -> list[tuple[CopilotConclusionReview, str]]:
        statement = (
            select(CopilotConclusionReview, User.email)
            .join(User, User.id == CopilotConclusionReview.reviewer_user_id)
            .where(CopilotConclusionReview.claim_id == claim_id)
            .order_by(CopilotConclusionReview.reviewed_at.desc())
        )
        return list(self.session.execute(statement).all())
