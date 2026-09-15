from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AnalysisResultStatus,
    AnalysisRunStatus,
    Claim,
    ClaimConsistencyCheck,
    ClaimStatus,
    DamageAnalysis,
    DocumentAnalysis,
    DocumentAnalysisField,
    DocumentFieldValidation,
    DocumentOcrResult,
    Evidence,
    EvidenceCategory,
    WorkflowAnalysisDamage,
    WorkflowAnalysisRun,
)
from app.services.document_analysis import DocumentAnalysisResult

if TYPE_CHECKING:
    from app.services.document_consistency import ConsistencyResult
    from app.services.document_field_validation import ValidatedDocumentField


class AnalysisRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, claim: Claim, input_revision: int) -> WorkflowAnalysisRun:
        run = WorkflowAnalysisRun(claim_id=claim.id, input_revision=input_revision)
        claim.status = ClaimStatus.ANALYZING
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def find(self, run_id: int) -> WorkflowAnalysisRun | None:
        return self.session.get(WorkflowAnalysisRun, run_id)

    def latest_for_claim(self, claim_id: int) -> WorkflowAnalysisRun | None:
        statement = (
            select(WorkflowAnalysisRun)
            .where(WorkflowAnalysisRun.claim_id == claim_id)
            .order_by(WorkflowAnalysisRun.created_at.desc(), WorkflowAnalysisRun.id.desc())
        )
        return self.session.scalar(statement)

    def mark_processing(self, run: WorkflowAnalysisRun) -> None:
        run.status = AnalysisRunStatus.PROCESSING
        run.damage_status = AnalysisResultStatus.PROCESSING
        run.started_at = datetime.now(timezone.utc)
        self.session.commit()

    def attach_damage(self, run: WorkflowAnalysisRun, analysis: DamageAnalysis) -> None:
        run.damage_status = AnalysisResultStatus.COMPLETED
        self.session.add(
            WorkflowAnalysisDamage(analysis_run_id=run.id, damage_analysis_id=analysis.id)
        )
        self.session.commit()

    def mark_damage_failed(self, run: WorkflowAnalysisRun, reason: str) -> None:
        run.damage_status = AnalysisResultStatus.FAILED
        run.failure_reason = reason
        self.session.commit()

    def fail(self, run: WorkflowAnalysisRun, claim: Claim, reason: str) -> None:
        run.status = AnalysisRunStatus.FAILED
        if run.damage_status in {AnalysisResultStatus.PENDING, AnalysisResultStatus.PROCESSING}:
            run.damage_status = AnalysisResultStatus.FAILED
        run.failure_reason = reason
        run.completed_at = datetime.now(timezone.utc)
        claim.status = ClaimStatus.FAILED
        self.session.commit()

    def save_document_result(
        self,
        run: WorkflowAnalysisRun,
        category: EvidenceCategory,
        status: AnalysisResultStatus,
        result: DocumentAnalysisResult | None = None,
        warning: str | None = None,
    ) -> DocumentAnalysis:
        warnings = result.warnings if result else ([warning] if warning else [])
        analysis = DocumentAnalysis(
            analysis_run_id=run.id,
            document_type=category,
            status=status,
            warnings_json=json.dumps(warnings),
        )
        self.session.add(analysis)
        self.session.flush()
        if result:
            self.session.add_all(
                [
                    DocumentAnalysisField(
                        document_analysis_id=analysis.id,
                        key=field.key,
                        label=field.label,
                        original_ai_value=field.value,
                        reviewed_value=field.value,
                        confidence=field.confidence,
                        status=field.status,
                    )
                    for field in result.fields
                ]
            )
        self.session.commit()
        self.session.refresh(analysis)
        return analysis

    def create_document_ocr_result(
        self, run: WorkflowAnalysisRun, evidence: Evidence
    ) -> DocumentOcrResult:
        result = DocumentOcrResult(
            analysis_run_id=run.id,
            evidence_id=evidence.id,
            document_type=evidence.category,
            original_filename=evidence.original_filename,
            content_type=evidence.content_type,
            status=AnalysisResultStatus.PENDING,
        )
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result

    def update_document_ocr_result(
        self,
        result: DocumentOcrResult,
        status: AnalysisResultStatus,
        *,
        raw_text: str | None = None,
        adapter_name: str | None = None,
        adapter_metadata: dict[str, object] | None = None,
        warning: str | None = None,
    ) -> DocumentOcrResult:
        result.status = status
        if raw_text is not None:
            result.raw_text = raw_text
        if adapter_name is not None:
            result.adapter_name = adapter_name
        if adapter_metadata is not None:
            result.adapter_metadata_json = json.dumps(adapter_metadata)
        result.warning = warning
        if status in {AnalysisResultStatus.COMPLETED, AnalysisResultStatus.FAILED}:
            result.processed_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(result)
        return result

    def complete(self, run: WorkflowAnalysisRun, claim: Claim) -> None:
        result_statuses = [run.damage_status] + [item.status for item in self.documents(run.id)]
        successful = sum(status is AnalysisResultStatus.COMPLETED for status in result_statuses)
        if successful == len(result_statuses):
            run.status = AnalysisRunStatus.COMPLETED
        elif successful:
            run.status = AnalysisRunStatus.PARTIAL
        else:
            run.status = AnalysisRunStatus.FAILED
        claim.status = ClaimStatus.REVIEW_REQUIRED if successful else ClaimStatus.FAILED
        run.completed_at = datetime.now(timezone.utc)
        self.session.commit()

    def damage_analysis(self, run_id: int) -> DamageAnalysis | None:
        statement = (
            select(DamageAnalysis)
            .join(WorkflowAnalysisDamage, WorkflowAnalysisDamage.damage_analysis_id == DamageAnalysis.id)
            .where(WorkflowAnalysisDamage.analysis_run_id == run_id)
        )
        return self.session.scalar(statement)

    def documents(self, run_id: int) -> list[DocumentAnalysis]:
        return list(
            self.session.scalars(
                select(DocumentAnalysis)
                .where(DocumentAnalysis.analysis_run_id == run_id)
                .order_by(DocumentAnalysis.id)
            )
        )

    def document_ocr_results(self, run_id: int) -> list[DocumentOcrResult]:
        return list(
            self.session.scalars(
                select(DocumentOcrResult)
                .where(DocumentOcrResult.analysis_run_id == run_id)
                .order_by(DocumentOcrResult.id)
            )
        )

    def save_field_validations(
        self,
        run: WorkflowAnalysisRun,
        ocr_result: DocumentOcrResult,
        validations: list[ValidatedDocumentField],
    ) -> list[DocumentFieldValidation]:
        records = [
            DocumentFieldValidation(
                analysis_run_id=run.id,
                document_ocr_result_id=ocr_result.id,
                source_evidence_id=validation.source_evidence_id,
                field_key=validation.field_key,
                prompt_version=validation.prompt_version,
                ocr_value=validation.ocr_value,
                normalized_value=validation.normalized_value,
                status=validation.status,
                confidence=validation.confidence,
                summary=validation.summary,
                warnings_json=json.dumps(validation.warnings),
            )
            for validation in validations
        ]
        self.session.add_all(records)
        self.session.commit()
        for record in records:
            self.session.refresh(record)
        return records

    def field_validations_for_ocr(
        self, document_ocr_result_id: int
    ) -> list[DocumentFieldValidation]:
        return list(
            self.session.scalars(
                select(DocumentFieldValidation)
                .where(
                    DocumentFieldValidation.document_ocr_result_id
                    == document_ocr_result_id
                )
                .order_by(DocumentFieldValidation.id)
            )
        )

    def field_validations(self, run_id: int) -> list[DocumentFieldValidation]:
        return list(
            self.session.scalars(
                select(DocumentFieldValidation)
                .where(DocumentFieldValidation.analysis_run_id == run_id)
                .order_by(DocumentFieldValidation.id)
            )
        )

    def save_consistency_checks(
        self,
        run: WorkflowAnalysisRun,
        validation_records: list[DocumentFieldValidation],
        results: list[ConsistencyResult],
    ) -> list[ClaimConsistencyCheck]:
        validation_by_source_and_key = {
            (record.source_evidence_id, record.field_key): record
            for record in validation_records
        }
        records = [
            ClaimConsistencyCheck(
                analysis_run_id=run.id,
                field_validation_id=validation_by_source_and_key[
                    (result.source_evidence_id, result.field_key)
                ].id,
                source_evidence_id=result.source_evidence_id,
                field_key=result.field_key,
                claim_value=result.claim_value,
                document_value=result.document_value,
                status=result.status,
                explanation=result.explanation,
            )
            for result in results
        ]
        self.session.add_all(records)
        self.session.commit()
        for record in records:
            self.session.refresh(record)
        return records

    def consistency_checks(self, run_id: int) -> list[ClaimConsistencyCheck]:
        return list(
            self.session.scalars(
                select(ClaimConsistencyCheck)
                .where(ClaimConsistencyCheck.analysis_run_id == run_id)
                .order_by(ClaimConsistencyCheck.id)
            )
        )

    def fields(self, document_analysis_id: int) -> list[DocumentAnalysisField]:
        return list(
            self.session.scalars(
                select(DocumentAnalysisField)
                .where(DocumentAnalysisField.document_analysis_id == document_analysis_id)
                .order_by(DocumentAnalysisField.id)
            )
        )

    def find_document_for_claim(
        self, claim_id: int, document_analysis_id: int
    ) -> DocumentAnalysis | None:
        statement = (
            select(DocumentAnalysis)
            .join(WorkflowAnalysisRun, WorkflowAnalysisRun.id == DocumentAnalysis.analysis_run_id)
            .where(
                WorkflowAnalysisRun.claim_id == claim_id,
                DocumentAnalysis.id == document_analysis_id,
            )
        )
        return self.session.scalar(statement)

    def update_field(
        self,
        document_analysis: DocumentAnalysis,
        field_id: int,
        reviewed_value: str,
    ) -> DocumentAnalysisField | None:
        field = self.session.scalar(
            select(DocumentAnalysisField).where(
                DocumentAnalysisField.document_analysis_id == document_analysis.id,
                DocumentAnalysisField.id == field_id,
            )
        )
        if field is None:
            return None
        field.reviewed_value = reviewed_value.strip()
        self.session.commit()
        self.session.refresh(field)
        return field
