from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Claim, ClaimIncident
from app.schemas.claims import IncidentInformation


class ClaimIncidentRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_for_claim(self, claim_id: int) -> ClaimIncident | None:
        return self.session.scalar(select(ClaimIncident).where(ClaimIncident.claim_id == claim_id))

    def save(self, claim: Claim, data: IncidentInformation) -> ClaimIncident:
        incident = self.find_for_claim(claim.id)
        occurred_at = data.occurred_at.astimezone(timezone.utc)
        if incident is None:
            incident = ClaimIncident(claim_id=claim.id, occurred_at=occurred_at, input_revision=1)
            self.session.add(incident)
        else:
            incident.input_revision += 1
        incident.occurred_at = occurred_at
        incident.location = data.location.strip()
        incident.description = data.description.strip()
        return incident

    def touch(self, claim_id: int) -> None:
        incident = self.find_for_claim(claim_id)
        if incident:
            incident.input_revision += 1
