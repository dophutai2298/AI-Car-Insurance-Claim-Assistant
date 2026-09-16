from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import AdjusterUser, CurrentUser
from app.core.config import Settings, get_settings
from app.db import get_db
from app.models import EvidenceCategory
from app.schemas.claims import (
    ClaimCreateRequest,
    ClaimInformationUpdateRequest,
    ClaimListItem,
    ClaimResponse,
    ClaimStatusUpdateRequest,
    CopilotConclusionReviewRequest,
    CopilotConclusionReviewRevertRequest,
    DamageAnalysisResponse,
    DocumentAnalysisFieldUpdateRequest,
    DocumentFieldValidationUpdateRequest,
    WorkflowAnalysisRunResponse,
)
from app.services.claims import ClaimService, EvidencePersistenceError
from app.repositories.assessment_rules import AssessmentRuleRepository
from app.services.assessment_rules import AssessmentRuleService
from app.services.damage_assessment import DamageAssessmentService
from app.services.damage_model import DamageModelUnavailableError, get_damage_model_adapter
from app.services.evidence_storage import EvidenceStorageError, LocalEvidenceStorage
from app.services.part_search import PartSearchService, get_part_price_provider
from app.services.llm_copilot import LlmCopilotService, get_llm_copilot_adapter
from app.repositories.vehicle_manufacturers import VehicleManufacturerRepository
from app.services.vehicle_manufacturers import VehicleManufacturerService
from app.services.document_analysis import MockDocumentAnalysisAdapter
from app.services.document_ocr import get_document_ocr_adapter
from app.services.document_consistency import ClaimConsistencyService
from app.services.document_field_validation import (
    DocumentFieldValidationService,
    get_document_field_validation_adapter,
)

router = APIRouter(prefix="/api/claims", tags=["claims"])


def build_claim_service(session: Session, settings: Settings) -> ClaimService:
    return ClaimService(
        session,
        LocalEvidenceStorage(settings),
        get_damage_model_adapter(settings),
        DamageAssessmentService(),
        AssessmentRuleService(AssessmentRuleRepository(session), settings),
        PartSearchService(get_part_price_provider(settings)),
        LlmCopilotService(get_llm_copilot_adapter(settings)),
        settings.openai_model,
        VehicleManufacturerService(VehicleManufacturerRepository(session)),
        MockDocumentAnalysisAdapter(),
        get_document_ocr_adapter(settings.document_ocr_mode),
        settings.document_ocr_mode == "mock",
        DocumentFieldValidationService(get_document_field_validation_adapter(settings)),
        ClaimConsistencyService(),
    )


def get_claim_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClaimService:
    return build_claim_service(session, settings)


def process_analysis_in_background(session_factory, settings: Settings, run_id: int) -> None:
    with session_factory() as session:
        build_claim_service(session, settings).process_workflow_analysis(run_id)


ClaimServiceDependency = Annotated[ClaimService, Depends(get_claim_service)]


@router.post("", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
def create_claim(
    request: ClaimCreateRequest,
    current_user: CurrentUser,
    service: ClaimServiceDependency,
) -> ClaimResponse:
    try:
        return service.create_claim(request, current_user)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.get("", response_model=list[ClaimListItem])
def list_claims(
    _current_user: CurrentUser,
    service: ClaimServiceDependency,
) -> list[ClaimListItem]:
    return service.list_claims()


@router.get("/{claim_number}", response_model=ClaimResponse)
def get_claim(
    claim_number: str,
    _current_user: CurrentUser,
    service: ClaimServiceDependency,
) -> ClaimResponse:
    claim = service.get_claim(claim_number)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.patch("/{claim_number}/status", response_model=ClaimResponse)
def transition_claim_status(
    claim_number: str,
    request: ClaimStatusUpdateRequest,
    _current_user: CurrentUser,
    service: ClaimServiceDependency,
) -> ClaimResponse:
    try:
        claim = service.transition_claim(claim_number, request.status)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Invalid claim lifecycle transition"
        ) from error
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.post("/{claim_number}/evidence", response_model=ClaimResponse)
def upload_evidence(
    claim_number: str,
    files: Annotated[list[UploadFile], File()],
    categories: Annotated[list[EvidenceCategory], Form()],
    _current_user: CurrentUser,
    service: ClaimServiceDependency,
    other_document_label: Annotated[str | None, Form()] = None,
) -> ClaimResponse:
    try:
        claim = service.upload_evidence(claim_number, categories, files, other_document_label)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except (EvidenceStorageError, EvidencePersistenceError) as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)) from error
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.get("/{claim_number}/evidence/{evidence_id}/content")
def get_evidence_content(
    claim_number: str,
    evidence_id: int,
    _current_user: CurrentUser,
    service: ClaimServiceDependency,
) -> FileResponse:
    evidence_with_path = service.evidence_content_path(claim_number, evidence_id)
    if evidence_with_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    evidence, path = evidence_with_path
    return FileResponse(path, media_type=evidence.content_type, filename=evidence.original_filename)


@router.post("/{claim_number}/damage-analysis", response_model=DamageAnalysisResponse)
def run_damage_analysis(
    claim_number: str,
    _current_user: CurrentUser,
    service: ClaimServiceDependency,
    force_reference_price_lookup: bool = False,
) -> DamageAnalysisResponse:
    try:
        analysis = service.run_damage_analysis(claim_number, force_reference_price_lookup)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except DamageModelUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return analysis


@router.post("/{claim_number}/copilot-conclusions/{conclusion_id}/review", response_model=ClaimResponse)
def review_copilot_conclusion(
    claim_number: str,
    conclusion_id: int,
    request: CopilotConclusionReviewRequest,
    current_user: AdjusterUser,
    service: ClaimServiceDependency,
) -> ClaimResponse:
    try:
        claim = service.review_copilot_conclusion(claim_number, conclusion_id, request, current_user)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI conclusion not found") from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.delete("/{claim_number}/evidence/{evidence_id}", response_model=ClaimResponse)
def delete_evidence(
    claim_number: str,
    evidence_id: int,
    _current_user: AdjusterUser,
    service: ClaimServiceDependency,
) -> ClaimResponse:
    try:
        claim = service.delete_evidence(claim_number, evidence_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.patch("/{claim_number}/information", response_model=ClaimResponse)
def update_claim_information(
    claim_number: str,
    request: ClaimInformationUpdateRequest,
    _current_user: AdjusterUser,
    service: ClaimServiceDependency,
) -> ClaimResponse:
    try:
        claim = service.update_claim_information(claim_number, request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.post(
    "/{claim_number}/analysis-runs",
    response_model=WorkflowAnalysisRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_workflow_analysis(
    claim_number: str,
    background_tasks: BackgroundTasks,
    request: Request,
    _current_user: AdjusterUser,
    service: ClaimServiceDependency,
    settings: Annotated[Settings, Depends(get_settings)],
) -> WorkflowAnalysisRunResponse:
    try:
        run = service.start_workflow_analysis(claim_number)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    background_tasks.add_task(
        process_analysis_in_background,
        request.app.state.session_factory,
        settings,
        run.id,
    )
    return run


@router.patch(
    "/{claim_number}/document-analyses/{document_analysis_id}/fields/{field_id}",
    response_model=ClaimResponse,
)
def update_document_analysis_field(
    claim_number: str,
    document_analysis_id: int,
    field_id: int,
    request: DocumentAnalysisFieldUpdateRequest,
    _current_user: AdjusterUser,
    service: ClaimServiceDependency,
) -> ClaimResponse:
    try:
        claim = service.update_document_analysis_field(
            claim_number, document_analysis_id, field_id, request
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.patch(
    "/{claim_number}/analysis-runs/{run_id}/field-validations/{field_validation_id}",
    response_model=ClaimResponse,
)
def update_document_field_validation(
    claim_number: str,
    run_id: int,
    field_validation_id: int,
    request: DocumentFieldValidationUpdateRequest,
    _current_user: AdjusterUser,
    service: ClaimServiceDependency,
) -> ClaimResponse:
    try:
        claim = service.update_document_field_validation(
            claim_number, run_id, field_validation_id, request
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.post(
    "/{claim_number}/analysis-runs/{run_id}/ai-review",
    response_model=ClaimResponse,
)
def run_workflow_ai_review(
    claim_number: str,
    run_id: int,
    _current_user: AdjusterUser,
    service: ClaimServiceDependency,
) -> ClaimResponse:
    try:
        claim = service.run_workflow_ai_review(claim_number, run_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.post(
    "/{claim_number}/copilot-conclusions/{conclusion_id}/review/revert",
    response_model=ClaimResponse,
)
def revert_copilot_conclusion_review(
    claim_number: str,
    conclusion_id: int,
    request: CopilotConclusionReviewRevertRequest,
    current_user: AdjusterUser,
    service: ClaimServiceDependency,
) -> ClaimResponse:
    try:
        claim = service.revert_copilot_conclusion_review(
            claim_number, conclusion_id, request, current_user
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim
