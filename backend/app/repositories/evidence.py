from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Claim,
    Evidence,
    EvidenceCategory,
    EvidenceRemoval,
    DamageDetection,
    DocumentOcrResult,
    OtherDocumentGroup,
    OtherDocumentGroupEvidence,
)


class StoredEvidenceRecord(Protocol):
    relative_path: str
    original_filename: str
    content_type: str | None
    file_size: int


class EvidenceRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_claim(self, claim_id: int) -> list[Evidence]:
        statement = (
            select(Evidence)
            .outerjoin(EvidenceRemoval, EvidenceRemoval.evidence_id == Evidence.id)
            .where(Evidence.claim_id == claim_id, EvidenceRemoval.id.is_(None))
            .order_by(Evidence.uploaded_at.desc())
        )
        return list(self.session.scalars(statement))

    def list_all_for_claim(self, claim_id: int) -> list[Evidence]:
        statement = select(Evidence).where(Evidence.claim_id == claim_id).order_by(Evidence.uploaded_at.desc())
        return list(self.session.scalars(statement))

    def find_for_claim(self, claim_id: int, evidence_id: int) -> Evidence | None:
        statement = (
            select(Evidence)
            .outerjoin(EvidenceRemoval, EvidenceRemoval.evidence_id == Evidence.id)
            .where(
                Evidence.claim_id == claim_id,
                Evidence.id == evidence_id,
                EvidenceRemoval.id.is_(None),
            )
        )
        return self.session.scalar(statement)

    def find_any_for_claim(self, claim_id: int, evidence_id: int) -> Evidence | None:
        statement = select(Evidence).where(Evidence.claim_id == claim_id, Evidence.id == evidence_id)
        return self.session.scalar(statement)

    def create_many(
        self,
        claim: Claim,
        uploads: list[tuple[EvidenceCategory, StoredEvidenceRecord]],
        other_document_label: str | None = None,
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
        self.session.flush()
        other_evidence = [
            item
            for item, (category, _) in zip(evidence, uploads, strict=True)
            if category is EvidenceCategory.OTHER_DOCUMENT
        ]
        if other_evidence:
            group = OtherDocumentGroup(claim_id=claim.id, label=other_document_label or "Other document")
            self.session.add(group)
            self.session.flush()
            self.session.add_all(
                [
                    OtherDocumentGroupEvidence(group_id=group.id, evidence_id=item.id)
                    for item in other_evidence
                ]
            )
        claim.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        for item in evidence:
            self.session.refresh(item)
        return evidence

    def group_details_for_claim(self, claim_id: int) -> dict[int, tuple[int, str]]:
        statement = (
            select(OtherDocumentGroupEvidence.evidence_id, OtherDocumentGroup.id, OtherDocumentGroup.label)
            .join(OtherDocumentGroup, OtherDocumentGroup.id == OtherDocumentGroupEvidence.group_id)
            .where(OtherDocumentGroup.claim_id == claim_id)
        )
        return {
            evidence_id: (group_id, label)
            for evidence_id, group_id, label in self.session.execute(statement).all()
        }

    def delete(self, evidence: Evidence) -> None:
        association = self.session.scalar(
            select(OtherDocumentGroupEvidence).where(
                OtherDocumentGroupEvidence.evidence_id == evidence.id
            )
        )
        group_id = association.group_id if association else None
        if association:
            self.session.delete(association)
        self.session.delete(evidence)
        self.session.flush()
        if group_id is not None:
            remaining = self.session.scalar(
                select(OtherDocumentGroupEvidence.id).where(
                    OtherDocumentGroupEvidence.group_id == group_id
                )
            )
            if remaining is None:
                group = self.session.get(OtherDocumentGroup, group_id)
                if group:
                    self.session.delete(group)
        self.session.commit()

    def is_referenced_by_analysis(self, evidence_id: int) -> bool:
        document_reference = self.session.scalar(
            select(DocumentOcrResult.id).where(DocumentOcrResult.evidence_id == evidence_id)
        )
        if document_reference is not None:
            return True
        statement = select(DamageDetection.id).where(
            (DamageDetection.source_evidence_id == evidence_id)
            | (DamageDetection.annotated_evidence_id == evidence_id)
        )
        return self.session.scalar(statement) is not None

    def mark_removed(self, evidence: Evidence) -> None:
        self.session.add(EvidenceRemoval(evidence_id=evidence.id))
        self.session.commit()
