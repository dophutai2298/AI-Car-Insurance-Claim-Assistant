from dataclasses import dataclass
import re
import unicodedata

from app.models import ConsistencyStatus
from app.services.document_field_validation import ValidatedDocumentField


NAME_FIELD_KEYS = {"full_name", "insured_name", "owner_name", "holder_name"}


def normalize_for_comparison(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    without_diacritics = "".join(character for character in decomposed if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]", "", without_diacritics)


@dataclass(frozen=True)
class ClaimFacts:
    claimant_name: str
    vehicle_make: str
    license_plate: str | None


@dataclass(frozen=True)
class ConsistencyResult:
    field_key: str
    source_evidence_id: int
    claim_value: str
    document_value: str
    status: ConsistencyStatus
    explanation: str


class ClaimConsistencyService:
    def compare(
        self, claim: ClaimFacts, fields: list[ValidatedDocumentField]
    ) -> list[ConsistencyResult]:
        results: list[ConsistencyResult] = []
        for field in fields:
            claim_value = self._claim_value(field.field_key, claim)
            document_value = field.normalized_value or field.ocr_value
            if not claim_value or not document_value:
                continue
            matches = normalize_for_comparison(claim_value) == normalize_for_comparison(document_value)
            results.append(
                ConsistencyResult(
                    field_key=field.field_key,
                    source_evidence_id=field.source_evidence_id,
                    claim_value=claim_value,
                    document_value=document_value,
                    status=ConsistencyStatus.MATCH if matches else ConsistencyStatus.MISMATCH,
                    explanation=(
                        "Document value matches Claim Information."
                        if matches
                        else "Document value differs from Claim Information and requires manual review."
                    ),
                )
            )
        return results

    @staticmethod
    def _claim_value(field_key: str, claim: ClaimFacts) -> str | None:
        if field_key in NAME_FIELD_KEYS:
            return claim.claimant_name
        if field_key == "vehicle_make":
            return claim.vehicle_make
        if field_key == "license_plate":
            return claim.license_plate
        return None
