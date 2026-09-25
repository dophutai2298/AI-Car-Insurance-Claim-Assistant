import logging
from pathlib import Path

from app.models import AnalysisResultStatus, Claim, DocumentFieldValidation, DocumentOcrResult, Evidence, EvidenceCategory, WorkflowAnalysisRun
from app.repositories.analysis_runs import AnalysisRunRepository
from app.services.document_analysis import DocumentAnalysisAdapter, DocumentAnalysisResult
from app.services.document_consistency import ClaimConsistencyService, ClaimFacts
from app.services.document_extraction import DocumentExtractionService
from app.services.document_extraction import SCHEMA_VERSION as DOCUMENT_EXTRACTION_SCHEMA_VERSION
from app.services.document_field_validation import DocumentFieldValidationService, ValidatedDocumentField
from app.services.document_ocr import DocumentOcrAdapter, DocumentOcrError
from app.services.evidence_storage import EvidenceStorage, EvidenceStorageError

SUPPORTED_DOCUMENT_IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
logger = logging.getLogger(__name__)


class DocumentAnalysisPipeline:
    def __init__(
        self,
        analysis_runs: AnalysisRunRepository,
        storage: EvidenceStorage,
        document_analysis: DocumentAnalysisAdapter,
        document_ocr: DocumentOcrAdapter,
        use_mock_document_fields: bool,
        document_extraction: DocumentExtractionService,
        document_field_validation: DocumentFieldValidationService,
        claim_consistency: ClaimConsistencyService,
    ) -> None:
        self.analysis_runs = analysis_runs
        self.storage = storage
        self.document_analysis = document_analysis
        self.document_ocr = document_ocr
        self.use_mock_document_fields = use_mock_document_fields
        self.document_extraction = document_extraction
        self.document_field_validation = document_field_validation
        self.claim_consistency = claim_consistency

    def process(
        self,
        run: WorkflowAnalysisRun,
        previous_run: WorkflowAnalysisRun | None,
        claim: Claim,
        by_category: dict[EvidenceCategory, list[Evidence]],
    ) -> None:
        ocr_by_category = {
            category: self._process_document_ocr_category(run, category, items)
            for category, items in by_category.items()
            if category is not EvidenceCategory.VEHICLE_DAMAGE_IMAGE
        }
        self._extract_document_fields(run, previous_run, ocr_by_category)
        self._validate_document_fields(run, claim)

    def _extract_document_fields(
        self,
        run: WorkflowAnalysisRun,
        previous_run: WorkflowAnalysisRun | None,
        ocr_by_category: dict[EvidenceCategory, list[DocumentOcrResult]],
    ) -> None:
        for category, ocr_results in ocr_by_category.items():
            completed = [
                result
                for result in ocr_results
                if result.status is AnalysisResultStatus.COMPLETED and result.raw_text
            ]
            if not completed or not self.document_extraction.supports(category):
                continue
            previous_ocr = (
                [
                    result
                    for result in self.analysis_runs.document_ocr_results(previous_run.id)
                    if result.document_type is category
                ]
                if previous_run
                else []
            )
            unchanged = {result.evidence_id for result in previous_ocr} == {
                result.evidence_id for result in ocr_results
            }
            previous_extraction = (
                self.analysis_runs.document_extraction_for_category(
                    previous_run.id,
                    category,
                    DOCUMENT_EXTRACTION_SCHEMA_VERSION,
                )
                if previous_run and unchanged
                else None
            )
            if (
                previous_extraction is None
                and previous_run
                and unchanged
                and len(ocr_results) == 1
            ):
                previous_extraction = self.analysis_runs.document_extraction_for_category(
                    previous_run.id,
                    category,
                )
            representative = completed[0]
            if previous_extraction is not None:
                self.analysis_runs.copy_document_extraction(
                    run,
                    representative,
                    previous_extraction,
                    DOCUMENT_EXTRACTION_SCHEMA_VERSION,
                )
                self.analysis_runs.mark_document_extraction_reuse(
                    representative,
                    reused=True,
                    source_run_id=previous_extraction.analysis_run_id,
                )
                continue
            combined_ocr = "\n\n".join(
                f"--- SOURCE: {result.original_filename} ---\n{result.raw_text}"
                for result in completed
            )
            outcome = self.document_extraction.extract(
                category,
                combined_ocr,
            )
            self.analysis_runs.save_document_extraction(run, representative, outcome)
            self.analysis_runs.mark_document_extraction_reuse(
                representative, reused=False
            )

    def _validate_document_fields(
        self, run: WorkflowAnalysisRun, claim: Claim
    ) -> None:
        claim_information = {
            "claimant_name": claim.claimant_name,
            "vehicle_make": claim.vehicle_make,
            "license_plate": claim.license_plate or "",
        }
        validated_fields: list[ValidatedDocumentField] = []
        validation_records: list[DocumentFieldValidation] = []
        for ocr_result in self.analysis_runs.document_ocr_results(run.id):
            if (
                ocr_result.status is not AnalysisResultStatus.COMPLETED
                or self.document_extraction.supports(ocr_result.document_type)
            ):
                continue
            validations = self.document_field_validation.validate_ocr_result(
                ocr_result.document_type,
                ocr_result.evidence_id,
                ocr_result.raw_text or "",
                claim_information,
            )
            validated_fields.extend(validations)
            validation_records.extend(
                self.analysis_runs.save_field_validations(run, ocr_result, validations)
            )

        consistency_results = self.claim_consistency.compare(
            ClaimFacts(
                claimant_name=claim.claimant_name,
                vehicle_make=claim.vehicle_make,
                license_plate=claim.license_plate,
            ),
            validated_fields,
        )
        self.analysis_runs.save_consistency_checks(
            run, validation_records, consistency_results
        )

    def _process_document_ocr_category(
        self, run: WorkflowAnalysisRun, category: EvidenceCategory, evidence_items: list[Evidence]
    ) -> list[DocumentOcrResult]:
        ocr_records = [
            (item, self.analysis_runs.create_document_ocr_result(run, item))
            for item in evidence_items
        ]
        warnings: list[str] = []
        statuses: list[AnalysisResultStatus] = []

        for evidence, record in ocr_records:
            reusable = self.analysis_runs.latest_document_ocr_for_evidence(
                evidence.id, run.id
            )
            if reusable is not None:
                self.analysis_runs.copy_document_ocr_result(record, reusable)
                if reusable.warning:
                    warnings.append(f"{evidence.original_filename}: {reusable.warning}")
                statuses.append(reusable.status)
                continue
            self.analysis_runs.update_document_ocr_result(record, AnalysisResultStatus.PROCESSING)
            if not self._supports_document_image(evidence):
                warning = "Only supported image evidence can be processed by OCR; this file was skipped."
                self.analysis_runs.update_document_ocr_result(
                    record, AnalysisResultStatus.FAILED, warning=warning
                )
                warnings.append(f"{evidence.original_filename}: {warning}")
                statuses.append(AnalysisResultStatus.FAILED)
                continue
            try:
                extracted = self.document_ocr.extract(
                    evidence, self.storage.resolve_path(evidence.stored_path)
                )
                self.analysis_runs.update_document_ocr_result(
                    record,
                    AnalysisResultStatus.COMPLETED,
                    raw_text=extracted.raw_text,
                    adapter_name=extracted.adapter_name,
                    adapter_metadata={**extracted.metadata, "ocr_reused": False},
                    warning=extracted.warning,
                )
                if extracted.warning:
                    warnings.append(f"{evidence.original_filename}: {extracted.warning}")
                statuses.append(AnalysisResultStatus.COMPLETED)
            except (DocumentOcrError, EvidenceStorageError) as error:
                warning = str(error) or "OCR processing failed."
                self.analysis_runs.update_document_ocr_result(
                    record, AnalysisResultStatus.FAILED, warning=warning
                )
                warnings.append(f"{evidence.original_filename}: {warning}")
                statuses.append(AnalysisResultStatus.FAILED)
            except Exception:
                logger.exception("OCR processing failed for run %s evidence %s", run.id, evidence.id)
                warning = "OCR processing failed unexpectedly."
                self.analysis_runs.update_document_ocr_result(
                    record, AnalysisResultStatus.FAILED, warning=warning
                )
                warnings.append(f"{evidence.original_filename}: {warning}")
                statuses.append(AnalysisResultStatus.FAILED)

        category_status = self._document_category_status(statuses)
        fallback_result: DocumentAnalysisResult | None = None
        if self.use_mock_document_fields and category_status is not AnalysisResultStatus.FAILED:
            try:
                fallback_result = self.document_analysis.analyze(category, evidence_items)
            except Exception:
                logger.exception("Mock document analysis failed for run %s", run.id)
                warnings.append("Mock document analysis failed.")

        self.analysis_runs.save_document_result(
            run,
            category,
            category_status,
            result=fallback_result,
            warning="; ".join(warnings) if warnings else None,
        )
        return [record for _, record in ocr_records]

    @staticmethod
    def _document_category_status(statuses: list[AnalysisResultStatus]) -> AnalysisResultStatus:
        if statuses and all(status is AnalysisResultStatus.COMPLETED for status in statuses):
            return AnalysisResultStatus.COMPLETED
        if any(status is AnalysisResultStatus.COMPLETED for status in statuses):
            return AnalysisResultStatus.PARTIAL
        return AnalysisResultStatus.FAILED

    @staticmethod
    def _supports_document_image(evidence: Evidence) -> bool:
        suffix = Path(evidence.original_filename).suffix.lower()
        content_type = (evidence.content_type or "").lower()
        return suffix in SUPPORTED_DOCUMENT_IMAGE_EXTENSIONS and (
            not content_type or content_type.startswith("image/")
        )
