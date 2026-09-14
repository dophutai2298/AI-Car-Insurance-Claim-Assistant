from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Claim, ClaimStatus
from app.schemas.claims import ClaimCreateRequest, ClaimInformationUpdateRequest


class ClaimRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: ClaimCreateRequest, created_by_user_id: int) -> Claim:
        claim = Claim(
            claimant_name=data.claimant_name.strip(),
            vehicle_make=data.vehicle.make.strip(),
            vehicle_model=data.vehicle.model.strip(),
            vehicle_year=data.vehicle.year,
            license_plate=data.vehicle.license_plate.strip() if data.vehicle.license_plate else None,
            vin=data.vehicle.vin.strip().upper() if data.vehicle.vin else None,
            status=ClaimStatus.DRAFT,
            created_by_user_id=created_by_user_id,
        )
        self.session.add(claim)
        self.session.flush()
        claim.claim_number = f"CLM-{claim.id:06d}"
        self.session.commit()
        self.session.refresh(claim)
        return claim

    def list_all(self) -> list[Claim]:
        return list(self.session.scalars(select(Claim).order_by(Claim.updated_at.desc())))

    def find_by_claim_number(self, claim_number: str) -> Claim | None:
        return self.session.scalar(select(Claim).where(Claim.claim_number == claim_number))

    def find_by_id(self, claim_id: int) -> Claim | None:
        return self.session.get(Claim, claim_id)

    def update_status(self, claim: Claim, status: ClaimStatus) -> Claim:
        claim.status = status
        self.session.commit()
        self.session.refresh(claim)
        return claim

    def update_information(self, claim: Claim, data: ClaimInformationUpdateRequest) -> Claim:
        claim.claimant_name = data.claimant_name.strip()
        claim.vehicle_make = data.vehicle.make.strip()
        claim.vehicle_model = data.vehicle.model.strip()
        claim.vehicle_year = data.vehicle.year
        claim.license_plate = data.vehicle.license_plate.strip() if data.vehicle.license_plate else None
        claim.vin = data.vehicle.vin.strip().upper() if data.vehicle.vin else None
        return claim
