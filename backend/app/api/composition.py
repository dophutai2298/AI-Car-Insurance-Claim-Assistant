from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.assessment_rules import AssessmentRuleRepository
from app.repositories.vehicle_manufacturers import VehicleManufacturerRepository
from app.services.assessment_rules import AssessmentRuleService
from app.services.claims import ClaimService
from app.services.damage_assessment import DamageAssessmentService
from app.services.damage_model import get_damage_model_adapter
from app.services.document_analysis import MockDocumentAnalysisAdapter
from app.services.document_consistency import ClaimConsistencyService
from app.services.document_extraction import DocumentExtractionService, DocumentPromptResolver, get_document_extraction_adapter
from app.services.document_field_validation import DocumentFieldValidationService, get_document_field_validation_adapter
from app.services.document_ocr import get_document_ocr_adapter
from app.services.evidence_storage import LocalEvidenceStorage
from app.services.llm_copilot import LlmCopilotService, get_llm_copilot_adapter
from app.services.part_search import PartSearchService, get_part_price_provider
from app.services.vehicle_manufacturers import VehicleManufacturerService


def build_claim_service(session: Session, settings: Settings) -> ClaimService:
    storage = LocalEvidenceStorage(settings)
    return ClaimService(
        session,
        storage,
        get_damage_model_adapter(settings, storage),
        DamageAssessmentService(),
        AssessmentRuleService(AssessmentRuleRepository(session), settings),
        PartSearchService(get_part_price_provider(settings)),
        LlmCopilotService(get_llm_copilot_adapter(settings)),
        settings.openai_model,
        VehicleManufacturerService(VehicleManufacturerRepository(session)),
        MockDocumentAnalysisAdapter(),
        get_document_ocr_adapter(settings.document_ocr_mode),
        settings.document_ocr_mode == "mock",
        DocumentExtractionService(get_document_extraction_adapter(settings), DocumentPromptResolver()),
        DocumentFieldValidationService(get_document_field_validation_adapter(settings)),
        ClaimConsistencyService(),
    )
