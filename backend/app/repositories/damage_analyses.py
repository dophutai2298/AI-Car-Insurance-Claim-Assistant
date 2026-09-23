import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.assessment_rules import AssessmentRuleValues
from app.models import (
    Claim,
    ClaimStatus,
    DamageAnalysis,
    DamageAnalysisRuleSnapshot,
    DamageDetection,
    DamageModelOutput,
    ReferencePartPrice,
)
from app.services.damage_assessment import AssessmentResult
from app.services.damage_model import DamageModelAnalysisResult, DamageModelDetection
from app.services.part_search import ReferencePartPriceResult


class DamageAnalysisRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        claim: Claim,
        assessment: AssessmentResult,
        model_result: DamageModelAnalysisResult,
        detections: list[DamageModelDetection],
        rules: AssessmentRuleValues,
        reference_prices: list[ReferencePartPriceResult],
        update_claim_status: bool = True,
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
        self.session.add(
            DamageModelOutput(
                analysis_id=analysis.id,
                adapter_name=model_result.adapter_name,
                output_json=json.dumps(model_result.to_dict(), ensure_ascii=False),
                warnings_json=json.dumps(list(model_result.warnings), ensure_ascii=False),
            )
        )
        self.session.add(
            DamageAnalysisRuleSnapshot(
                analysis_id=analysis.id,
                confidence_threshold=rules.confidence_threshold,
                repair_max_percentage=rules.repair_max_percentage,
                replacement_min_percentage=rules.replacement_min_percentage,
            )
        )
        self.session.add_all(
            [
                ReferencePartPrice(
                    analysis_id=analysis.id,
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
                for price in reference_prices
            ]
        )
        if update_claim_status:
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

    def rule_snapshot(self, analysis_id: int) -> DamageAnalysisRuleSnapshot | None:
        statement = select(DamageAnalysisRuleSnapshot).where(
            DamageAnalysisRuleSnapshot.analysis_id == analysis_id
        )
        return self.session.scalar(statement)

    def model_output(self, analysis_id: int) -> DamageModelOutput | None:
        statement = select(DamageModelOutput).where(
            DamageModelOutput.analysis_id == analysis_id
        )
        return self.session.scalar(statement)

    def reference_prices(self, analysis_id: int) -> list[ReferencePartPrice]:
        statement = (
            select(ReferencePartPrice)
            .where(ReferencePartPrice.analysis_id == analysis_id)
            .order_by(ReferencePartPrice.id)
        )
        return list(self.session.scalars(statement))
