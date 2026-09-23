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
    DocumentExtractedField,
    DocumentExtractionResult,
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
    from app.services.document_extraction import DocumentExtractionOutcome
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

    def latest_terminal_for_claim(self, claim_id: int) -> WorkflowAnalysisRun | None:
        statement = (
            select(WorkflowAnalysisRun)
            .where(
                WorkflowAnalysisRun.claim_id == claim_id,
                WorkflowAnalysisRun.status.in_(
                    [
                        AnalysisRunStatus.COMPLETED,
                        AnalysisRunStatus.PARTIAL,
                        AnalysisRunStatus.FAILED,
                    ]
                ),
            )
            .order_by(WorkflowAnalysisRun.created_at.desc(), WorkflowAnalysisRun.id.desc())
        )
        return self.session.scalar(statement)

    def latest_before(self, claim_id: int, run_id: int) -> WorkflowAnalysisRun | None:
        statement = (
            select(WorkflowAnalysisRun)
            .where(
                WorkflowAnalysisRun.claim_id == claim_id,
                WorkflowAnalysisRun.id < run_id,
            )
            .order_by(WorkflowAnalysisRun.id.desc())
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

    def latest_document_ocr_for_evidence(
        self, evidence_id: int, before_run_id: int
    ) -> DocumentOcrResult | None:
        statement = (
            select(DocumentOcrResult)
            .where(
                DocumentOcrResult.evidence_id == evidence_id,
                DocumentOcrResult.analysis_run_id < before_run_id,
                DocumentOcrResult.status.in_(
                    [AnalysisResultStatus.COMPLETED, AnalysisResultStatus.FAILED]
                ),
            )
            .order_by(DocumentOcrResult.analysis_run_id.desc(), DocumentOcrResult.id.desc())
        )
        return self.session.scalar(statement)

    def copy_document_ocr_result(
        self,
        target: DocumentOcrResult,
        source: DocumentOcrResult,
    ) -> DocumentOcrResult:
        metadata = json.loads(source.adapter_metadata_json)
        metadata.update(
            {
                "ocr_reused": True,
                "ocr_reused_from_analysis_run_id": source.analysis_run_id,
            }
        )
        return self.update_document_ocr_result(
            target,
            source.status,
            raw_text=source.raw_text,
            adapter_name=source.adapter_name,
            adapter_metadata=metadata,
            warning=source.warning,
        )

    def mark_document_extraction_reuse(
        self,
        ocr_result: DocumentOcrResult,
        *,
        reused: bool,
        source_run_id: int | None = None,
    ) -> None:
        metadata = json.loads(ocr_result.adapter_metadata_json)
        metadata["extraction_reused"] = reused
        if source_run_id is not None:
            metadata["extraction_reused_from_analysis_run_id"] = source_run_id
        else:
            metadata.pop("extraction_reused_from_analysis_run_id", None)
        ocr_result.adapter_metadata_json = json.dumps(metadata)
        self.session.commit()

    def save_document_extraction(
        self,
        run: WorkflowAnalysisRun,
        ocr_result: DocumentOcrResult,
        outcome: DocumentExtractionOutcome,
    ) -> DocumentExtractionResult:
        extraction = DocumentExtractionResult(
            analysis_run_id=run.id,
            document_ocr_result_id=ocr_result.id,
            source_evidence_id=ocr_result.evidence_id,
            document_type=ocr_result.document_type,
            status=outcome.status,
            prompt_version=outcome.prompt_version,
            schema_version=outcome.schema_version,
            warning=outcome.warning,
            processed_at=datetime.now(timezone.utc),
        )
        self.session.add(extraction)
        self.session.flush()
        self.session.add_all(
            [
                DocumentExtractedField(
                    analysis_run_id=run.id,
                    extraction_result_id=extraction.id,
                    source_evidence_id=ocr_result.evidence_id,
                    field_key=field.field_key,
                    ai_extracted_value=field.value,
                    confirmed_value=field.value,
                    prompt_version=outcome.prompt_version,
                    schema_version=outcome.schema_version,
                )
                for field in outcome.fields
            ]
        )
        self.session.commit()
        self.session.refresh(extraction)
        return extraction

    def document_extraction_for_ocr(
        self, document_ocr_result_id: int
    ) -> DocumentExtractionResult | None:
        return self.session.scalar(
            select(DocumentExtractionResult).where(
                DocumentExtractionResult.document_ocr_result_id == document_ocr_result_id
            )
        )

    def document_extraction_for_category(
        self,
        run_id: int,
        category: EvidenceCategory,
        schema_version: str | None = None,
    ) -> DocumentExtractionResult | None:
        statement = select(DocumentExtractionResult).where(
            DocumentExtractionResult.analysis_run_id == run_id,
            DocumentExtractionResult.document_type == category,
            DocumentExtractionResult.status == AnalysisResultStatus.COMPLETED,
        )
        if schema_version is not None:
            statement = statement.where(
                DocumentExtractionResult.schema_version == schema_version
            )
        return self.session.scalar(statement.order_by(DocumentExtractionResult.id))

    def copy_document_extraction(
        self,
        run: WorkflowAnalysisRun,
        ocr_result: DocumentOcrResult,
        source: DocumentExtractionResult,
        schema_version: str | None = None,
    ) -> DocumentExtractionResult:
        target_schema_version = schema_version or source.schema_version
        extraction = DocumentExtractionResult(
            analysis_run_id=run.id,
            document_ocr_result_id=ocr_result.id,
            source_evidence_id=ocr_result.evidence_id,
            document_type=ocr_result.document_type,
            status=source.status,
            prompt_version=source.prompt_version,
            schema_version=target_schema_version,
            warning=source.warning,
            processed_at=datetime.now(timezone.utc),
        )
        self.session.add(extraction)
        self.session.flush()
        self.session.add_all(
            [
                DocumentExtractedField(
                    analysis_run_id=run.id,
                    extraction_result_id=extraction.id,
                    source_evidence_id=ocr_result.evidence_id,
                    field_key=field.field_key,
                    ai_extracted_value=field.ai_extracted_value,
                    confirmed_value=field.confirmed_value,
                    prompt_version=field.prompt_version,
                    schema_version=target_schema_version,
                )
                for field in self.extracted_fields_for_result(source.id)
            ]
        )
        self.session.commit()
        self.session.refresh(extraction)
        return extraction

    def extracted_fields_for_result(
        self, extraction_result_id: int
    ) -> list[DocumentExtractedField]:
        return list(
            self.session.scalars(
                select(DocumentExtractedField)
                .where(DocumentExtractedField.extraction_result_id == extraction_result_id)
                .order_by(DocumentExtractedField.id)
            )
        )

    def find_extracted_field_for_claim(
        self,
        claim_id: int,
        run_id: int,
        extracted_field_id: int,
    ) -> DocumentExtractedField | None:
        return self.session.scalar(
            select(DocumentExtractedField)
            .join(
                WorkflowAnalysisRun,
                WorkflowAnalysisRun.id == DocumentExtractedField.analysis_run_id,
            )
            .where(
                WorkflowAnalysisRun.claim_id == claim_id,
                WorkflowAnalysisRun.id == run_id,
                DocumentExtractedField.id == extracted_field_id,
            )
        )

    def find_extracted_fields_for_claim(
        self,
        claim_id: int,
        run_id: int,
        extracted_field_ids: list[int],
    ) -> list[DocumentExtractedField]:
        return list(
            self.session.scalars(
                select(DocumentExtractedField)
                .join(
                    WorkflowAnalysisRun,
                    WorkflowAnalysisRun.id == DocumentExtractedField.analysis_run_id,
                )
                .where(
                    WorkflowAnalysisRun.claim_id == claim_id,
                    WorkflowAnalysisRun.id == run_id,
                    DocumentExtractedField.id.in_(extracted_field_ids),
                )
            )
        )

    def extracted_fields(self, run_id: int) -> list[DocumentExtractedField]:
        return list(
            self.session.scalars(
                select(DocumentExtractedField)
                .where(DocumentExtractedField.analysis_run_id == run_id)
                .order_by(DocumentExtractedField.id)
            )
        )

    def update_extracted_field(
        self, field: DocumentExtractedField, confirmed_value: str | None
    ) -> DocumentExtractedField:
        field.confirmed_value = confirmed_value.strip() if confirmed_value else None
        self.session.commit()
        self.session.refresh(field)
        return field

    def update_extracted_fields(
        self,
        fields: list[DocumentExtractedField],
        values_by_id: dict[int, str | None],
    ) -> None:
        for field in fields:
            value = values_by_id[field.id]
            field.confirmed_value = value.strip() if value else None
        self.session.commit()

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

    def find_field_validation_for_claim(
        self,
        claim_id: int,
        run_id: int,
        field_validation_id: int,
    ) -> DocumentFieldValidation | None:
        return self.session.scalar(
            select(DocumentFieldValidation)
            .join(
                WorkflowAnalysisRun,
                WorkflowAnalysisRun.id == DocumentFieldValidation.analysis_run_id,
            )
            .where(
                WorkflowAnalysisRun.claim_id == claim_id,
                WorkflowAnalysisRun.id == run_id,
                DocumentFieldValidation.id == field_validation_id,
            )
        )

    def update_field_validation(
        self, validation: DocumentFieldValidation, reviewed_value: str
    ) -> DocumentFieldValidation:
        validation.normalized_value = reviewed_value.strip()
        self.session.commit()
        self.session.refresh(validation)
        return validation

    def update_consistency_check(
        self,
        validation: DocumentFieldValidation,
        result: ConsistencyResult,
    ) -> None:
        check = self.session.scalar(
            select(ClaimConsistencyCheck).where(
                ClaimConsistencyCheck.field_validation_id == validation.id
            )
        )
        if check is None:
            check = ClaimConsistencyCheck(
                analysis_run_id=validation.analysis_run_id,
                field_validation_id=validation.id,
                source_evidence_id=validation.source_evidence_id,
                field_key=validation.field_key,
                claim_value=result.claim_value,
                document_value=result.document_value,
                status=result.status,
                explanation=result.explanation,
            )
            self.session.add(check)
        else:
            check.claim_value = result.claim_value
            check.document_value = result.document_value
            check.status = result.status
            check.explanation = result.explanation
        self.session.commit()

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
