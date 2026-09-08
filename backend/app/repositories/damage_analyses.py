from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Claim, ClaimStatus, DamageAnalysis, DamageDetection
from app.services.damage_assessment import AssessmentResult
from app.services.damage_model import DamageModelDetection


class DamageAnalysisRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        claim: Claim,
        assessment: AssessmentResult,
        detections: list[DamageModelDetection],
    ) -> DamageAnalysis:
        analysis = DamageAnalysis(claim_id=claim.id, assessment=assessment.assessment, warning=assessment.warning)
        self.session.add(analysis)
        self.session.flush()
        analysis.analysis_number = f"DA-{analysis.id:06d}"
        self.session.add_all(
            [
                DamageDetection(
                    analysis_id=analysis.id,
                    source_evidence_id=detection.source_evidence_id,
                    annotated_evidence_id=detection.annotated_evidence_id,
                    vehicle_part=detection.vehicle_part,
                    damage_type=detection.damage_type,
                    damage_percentage=detection.damage_percentage,
                    confidence=detection.confidence,
                    status=detection.status,
                )
                for detection in detections
            ]
        )
        claim.status = ClaimStatus.REVIEW_REQUIRED
        self.session.commit()
        self.session.refresh(analysis)
        return analysis

    def latest_for_claim(self, claim_id: int) -> DamageAnalysis | None:
        statement = select(DamageAnalysis).where(DamageAnalysis.claim_id == claim_id).order_by(DamageAnalysis.created_at.desc())
        return self.session.scalar(statement)

    def list_detections(self, analysis_id: int) -> list[DamageDetection]:
        statement = select(DamageDetection).where(DamageDetection.analysis_id == analysis_id).order_by(DamageDetection.id)
        return list(self.session.scalars(statement))
