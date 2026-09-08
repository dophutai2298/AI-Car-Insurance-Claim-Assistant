from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db import get_db
from app.schemas.claims import ClaimCreateRequest, ClaimListItem, ClaimResponse, ClaimStatusUpdateRequest
from app.services.claims import ClaimService

router = APIRouter(prefix="/api/claims", tags=["claims"])


@router.post("", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
def create_claim(
    request: ClaimCreateRequest,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> ClaimResponse:
    return ClaimService(session).create_claim(request, current_user)


@router.get("", response_model=list[ClaimListItem])
def list_claims(
    _current_user: CurrentUser, session: Annotated[Session, Depends(get_db)]
) -> list[ClaimListItem]:
    return ClaimService(session).list_claims()


@router.get("/{claim_number}", response_model=ClaimResponse)
def get_claim(
    claim_number: str,
    _current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> ClaimResponse:
    claim = ClaimService(session).get_claim(claim_number)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.patch("/{claim_number}/status", response_model=ClaimResponse)
def transition_claim_status(
    claim_number: str,
    request: ClaimStatusUpdateRequest,
    _current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> ClaimResponse:
    try:
        claim = ClaimService(session).transition_claim(claim_number, request.status)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Invalid claim lifecycle transition"
        ) from error
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim
