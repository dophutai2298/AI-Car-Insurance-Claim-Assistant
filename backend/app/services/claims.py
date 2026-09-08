from sqlalchemy.orm import Session

from app.models import Claim, ClaimStatus, User
from app.repositories.claims import ClaimRepository
from app.schemas.claims import ClaimCreateRequest, ClaimListItem, ClaimResponse, VehicleMetadata

ALLOWED_LIFECYCLE_TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    ClaimStatus.DRAFT: {ClaimStatus.ANALYZING},
    ClaimStatus.ANALYZING: {ClaimStatus.REVIEW_REQUIRED, ClaimStatus.FAILED},
    ClaimStatus.FAILED: {ClaimStatus.ANALYZING},
}


class ClaimService:
    def __init__(self, session: Session):
        self.claims = ClaimRepository(session)

    def create_claim(self, data: ClaimCreateRequest, created_by: User) -> ClaimResponse:
        return self._to_response(self.claims.create(data, created_by.id))

    def list_claims(self) -> list[ClaimListItem]:
        return [
            ClaimListItem(
                id=claim.claim_number,
                claimant_name=claim.claimant_name,
                vehicle_summary=f"{claim.vehicle_year} {claim.vehicle_make} {claim.vehicle_model}",
                status=claim.status,
                updated_at=claim.updated_at,
            )
            for claim in self.claims.list_all()
            if claim.claim_number
        ]

    def get_claim(self, claim_number: str) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        return self._to_response(claim) if claim else None

    def transition_claim(self, claim_number: str, next_status: ClaimStatus) -> ClaimResponse | None:
        claim = self.claims.find_by_claim_number(claim_number)
        if claim is None:
            return None
        if next_status not in ALLOWED_LIFECYCLE_TRANSITIONS.get(claim.status, set()):
            raise ValueError("Invalid claim lifecycle transition")
        return self._to_response(self.claims.update_status(claim, next_status))

    @staticmethod
    def _to_response(claim: Claim) -> ClaimResponse:
        if claim.claim_number is None:
            raise ValueError("Claim number must be assigned before serialization")

        return ClaimResponse(
            id=claim.claim_number,
            claimant_name=claim.claimant_name,
            vehicle=VehicleMetadata(
                make=claim.vehicle_make,
                model=claim.vehicle_model,
                year=claim.vehicle_year,
                license_plate=claim.license_plate,
                vin=claim.vin,
            ),
            status=claim.status,
            created_at=claim.created_at,
            updated_at=claim.updated_at,
        )
