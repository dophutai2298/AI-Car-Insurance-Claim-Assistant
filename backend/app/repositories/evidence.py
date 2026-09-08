from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Claim, Evidence, EvidenceCategory


class StoredEvidenceRecord(Protocol):
    relative_path: str
    original_filename: str
    content_type: str | None
    file_size: int


class EvidenceRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_claim(self, claim_id: int) -> list[Evidence]:
        statement = select(Evidence).where(Evidence.claim_id == claim_id).order_by(Evidence.uploaded_at.desc())
        return list(self.session.scalars(statement))

    def find_for_claim(self, claim_id: int, evidence_id: int) -> Evidence | None:
        statement = select(Evidence).where(Evidence.claim_id == claim_id, Evidence.id == evidence_id)
        return self.session.scalar(statement)

    def create_many(
        self, claim: Claim, uploads: list[tuple[EvidenceCategory, StoredEvidenceRecord]]
    ) -> list[Evidence]:
        evidence = [
            Evidence(
                claim_id=claim.id,
                category=category,
                original_filename=upload.original_filename,
                stored_path=upload.relative_path,
                content_type=upload.content_type,
                file_size=upload.file_size,
            )
            for category, upload in uploads
        ]
        self.session.add_all(evidence)
        claim.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        for item in evidence:
            self.session.refresh(item)
        return evidence
