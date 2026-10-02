from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Claim, ClaimStatus, User, UserRole
from app.schemas.claims import ClaimCreateRequest, ClaimInformationUpdateRequest


class ClaimRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        data: ClaimCreateRequest,
        created_by_user_id: int,
        assigned_adjuster_user_id: int | None,
    ) -> Claim:
        claim = Claim(
            claimant_name=data.claimant_name.strip(),
            vehicle_make=data.vehicle.make.strip(),
            vehicle_model=data.vehicle.model.strip(),
            vehicle_year=data.vehicle.year,
            license_plate=data.vehicle.license_plate.strip() if data.vehicle.license_plate else None,
            vin=data.vehicle.vin.strip().upper() if data.vehicle.vin else None,
            status=ClaimStatus.DRAFT,
            created_by_user_id=created_by_user_id,
            assigned_adjuster_user_id=assigned_adjuster_user_id,
        )
        self.session.add(claim)
        self.session.flush()
        claim.claim_number = f"CLM-{claim.id:06d}"
        self.session.commit()
        self.session.refresh(claim)
        return claim

    def list_page(
        self,
        *,
        page: int,
        page_size: int,
        status: ClaimStatus | None = None,
        search: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> tuple[list[Claim], int]:
        filters = []
        if status is not None:
            filters.append(Claim.status == status)
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Claim.claim_number).like(term),
                    func.lower(Claim.claimant_name).like(term),
                    func.lower(Claim.vehicle_make).like(term),
                    func.lower(Claim.vehicle_model).like(term),
                    func.lower(Claim.license_plate).like(term),
                )
            )
        if updated_from is not None:
            filters.append(Claim.updated_at >= updated_from)
        if updated_to is not None:
            filters.append(Claim.updated_at <= updated_to)
        total = self.session.scalar(select(func.count(Claim.id)).where(*filters)) or 0
        statement = (
            select(Claim)
            .where(*filters)
            .order_by(Claim.updated_at.desc(), Claim.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def find_by_claim_number(self, claim_number: str) -> Claim | None:
        return self.session.scalar(select(Claim).where(Claim.claim_number == claim_number))

    def find_by_id(self, claim_id: int) -> Claim | None:
        return self.session.get(Claim, claim_id)

    def update_status(self, claim: Claim, status: ClaimStatus) -> Claim:
        claim.status = status
        self.session.commit()
        self.session.refresh(claim)
        return claim

    def assign(self, claim: Claim, adjuster: User) -> Claim:
        if adjuster.role is not UserRole.ADJUSTER or not adjuster.is_active:
            raise ValueError("Claim assignee must be an active adjuster")
        claim.assigned_adjuster_user_id = adjuster.id
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
