from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import Settings, get_settings
from app.db import get_db
from app.models import EvidenceCategory
from app.schemas.claims import (
    ClaimCreateRequest,
    ClaimListItem,
    ClaimResponse,
    ClaimStatusUpdateRequest,
    DamageAnalysisResponse,
)
from app.services.claims import ClaimService, EvidencePersistenceError
from app.repositories.assessment_rules import AssessmentRuleRepository
from app.services.assessment_rules import AssessmentRuleService
from app.services.damage_assessment import DamageAssessmentService
from app.services.damage_model import DamageModelUnavailableError, get_damage_model_adapter
from app.services.evidence_storage import EvidenceStorageError, LocalEvidenceStorage
from app.services.part_search import PartSearchService, get_part_price_provider
from app.services.llm_copilot import LlmCopilotService, get_llm_copilot_adapter

router = APIRouter(prefix="/api/claims", tags=["claims"])


def get_claim_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClaimService:
    return ClaimService(
        session,
        LocalEvidenceStorage(settings),
        get_damage_model_adapter(settings),
        DamageAssessmentService(),
        AssessmentRuleService(AssessmentRuleRepository(session), settings),
        PartSearchService(get_part_price_provider(settings)),
        LlmCopilotService(get_llm_copilot_adapter(settings)),
        settings.openai_model,
    )


ClaimServiceDependency = Annotated[ClaimService, Depends(get_claim_service)]


@router.post("", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
def create_claim(
    request: ClaimCreateRequest,
    current_user: CurrentUser,
    service: ClaimServiceDependency,
) -> ClaimResponse:
    return service.create_claim(request, current_user)


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
) -> ClaimResponse:
    try:
        claim = service.upload_evidence(claim_number, categories, files)
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
