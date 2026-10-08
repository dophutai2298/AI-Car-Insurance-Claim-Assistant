import json
from dataclasses import replace

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
    Evidence,
    EvidenceCategory,
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
        annotated_ids: dict[int, int] = {}
        for result in model_result.results:
            if result.annotation is None:
                continue
            annotation = result.annotation
            record = Evidence(
                claim_id=claim.id,
                category=EvidenceCategory.DAMAGE_ANNOTATION,
                original_filename=annotation.original_filename,
                stored_path=annotation.relative_path,
                content_type=annotation.content_type,
                file_size=annotation.file_size,
            )
            self.session.add(record)
            self.session.flush()
            annotated_ids[result.source_evidence_id] = record.id
        stored_result = replace(
            model_result,
            results=tuple(
                replace(
                    result,
                    annotated_evidence_id=annotated_ids.get(
                        result.source_evidence_id, result.annotated_evidence_id
                    ),
                )
                for result in model_result.results
            ),
        )
        self.session.add_all(
            [
                DamageDetection(
                    analysis_id=analysis.id,
                    source_evidence_id=detection.source_evidence_id,
                    annotated_evidence_id=annotated_ids.get(
                        detection.source_evidence_id, detection.annotated_evidence_id
                    ),
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
                output_json=json.dumps(stored_result.to_dict(), ensure_ascii=False),
                warnings_json=json.dumps(list(model_result.warnings), ensure_ascii=False),
            )
        )
        self._save_assessment_context(analysis.id, rules, reference_prices)
        if update_claim_status:
            claim.status = ClaimStatus.REVIEW_REQUIRED
        self.session.commit()
        self.session.refresh(analysis)
        return analysis

    def latest_for_claim(self, claim_id: int) -> DamageAnalysis | None:
        statement = select(DamageAnalysis).where(DamageAnalysis.claim_id == claim_id).order_by(DamageAnalysis.created_at.desc())
        return self.session.scalar(statement)

    def copy_for_run(
        self,
        source: DamageAnalysis,
        assessment: AssessmentResult,
        rules: AssessmentRuleValues,
        reference_prices: list[ReferencePartPriceResult],
    ) -> DamageAnalysis:
        output = self.model_output(source.id)
        if output is None:
            raise ValueError("Cannot reuse damage analysis without model output")
        analysis = DamageAnalysis(
            claim_id=source.claim_id,
            assessment=assessment.assessment,
            warning=assessment.warning,
        )
        self.session.add(analysis)
        self.session.flush()
        analysis.analysis_number = f"DA-{analysis.id:06d}"
        self.session.add_all(
            [
                DamageDetection(
                    analysis_id=analysis.id,
                    source_evidence_id=item.source_evidence_id,
                    annotated_evidence_id=item.annotated_evidence_id,
                    vehicle_part=item.vehicle_part,
                    damage_type=item.damage_type,
                    damage_percentage=item.damage_percentage,
                    confidence=item.confidence,
                    status=item.status,
                )
                for item in self.list_detections(source.id)
            ]
        )
        self.session.add(
            DamageModelOutput(
                analysis_id=analysis.id,
                adapter_name=output.adapter_name,
                output_json=output.output_json,
                warnings_json=output.warnings_json,
            )
        )
        self._save_assessment_context(analysis.id, rules, reference_prices)
        self.session.commit()
        self.session.refresh(analysis)
        return analysis

    def _save_assessment_context(
        self,
        analysis_id: int,
        rules: AssessmentRuleValues,
        reference_prices: list[ReferencePartPriceResult],
    ) -> None:
        self.session.add(
            DamageAnalysisRuleSnapshot(
                analysis_id=analysis_id,
                repair_max_percentage=rules.repair_max_percentage,
                replacement_min_percentage=rules.replacement_min_percentage,
            )
        )
        self.session.add_all(
            [
                ReferencePartPrice(
                    analysis_id=analysis_id,
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
