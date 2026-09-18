from dataclasses import dataclass
import re
import unicodedata

from app.models import ConsistencyStatus
from app.services.document_field_validation import ValidatedDocumentField


NAME_FIELD_KEYS = {
    "full_name",
    "insured_name",
    "owner_name",
    "holder_name",
    "vehicle_owner",
}
VEHICLE_MAKE_FIELD_KEYS = {"vehicle_make", "vehicle_brand"}


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
    claim_value: str | None
    document_value: str | None
    status: ConsistencyStatus
    explanation: str


class ClaimConsistencyService:
    def compare(
        self, claim: ClaimFacts, fields: list[ValidatedDocumentField]
    ) -> list[ConsistencyResult]:
        results: list[ConsistencyResult] = []
        for field in fields:
            document_value = field.normalized_value or field.ocr_value
            result = self.compare_value(
                claim,
                field.field_key,
                field.source_evidence_id,
                document_value,
            )
            if result is not None and result.status is not ConsistencyStatus.UNAVAILABLE:
                results.append(result)
        return results

    def compare_value(
        self,
        claim: ClaimFacts,
        field_key: str,
        source_evidence_id: int,
        document_value: str | None,
    ) -> ConsistencyResult | None:
        claim_value = self._claim_value(field_key, claim)
        if field_key not in NAME_FIELD_KEYS | VEHICLE_MAKE_FIELD_KEYS | {"license_plate"}:
            return None
        if not claim_value or not document_value:
            return ConsistencyResult(
                field_key=field_key,
                source_evidence_id=source_evidence_id,
                claim_value=claim_value,
                document_value=document_value,
                status=ConsistencyStatus.UNAVAILABLE,
                explanation="Comparison is unavailable because a claim or document value is missing.",
            )
        matches = normalize_for_comparison(claim_value) == normalize_for_comparison(
            document_value
        )
        return ConsistencyResult(
            field_key=field_key,
            source_evidence_id=source_evidence_id,
            claim_value=claim_value,
            document_value=document_value,
            status=ConsistencyStatus.MATCH if matches else ConsistencyStatus.MISMATCH,
            explanation=(
                "Document value matches Claim Information."
                if matches
                else "Document value differs from Claim Information and requires manual review."
            ),
        )

    @staticmethod
    def _claim_value(field_key: str, claim: ClaimFacts) -> str | None:
        if field_key in NAME_FIELD_KEYS:
            return claim.claimant_name
        if field_key in VEHICLE_MAKE_FIELD_KEYS:
            return claim.vehicle_make
        if field_key == "license_plate":
            return claim.license_plate
        return None
