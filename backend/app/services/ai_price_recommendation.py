import re
import unicodedata

from app.schemas.claims import AnalysisPricingResponse
from app.schemas.price_recommendation import PriceRecommendation

_UNSUPPORTED_CLAIMS = re.compile(
    r"\b(?:vnd|usd|eur|dollars?|million|billion|nghìn|ngàn|triệu|tỷ(?!\s+lệ)|"
    r"approv\w*|reject\w*|payout|settlement)\b|phê duyệt|chấp thuận|từ chối|bồi thường|chi trả",
    re.IGNORECASE,
)
_WRITTEN_DONG_AMOUNT = re.compile(
    r"\b(?:một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|trăm|one|two|three|ten|hundred|thousand)\s+(?:đồng|dong)\b",
    re.IGNORECASE,
)


def qualitative_rationale_is_safe(text: str) -> bool:
    return not (
        any(char.isdigit() or unicodedata.category(char) == "Sc" for char in text)
        or _UNSUPPORTED_CLAIMS.search(text)
        or _WRITTEN_DONG_AMOUNT.search(text)
    )


def enforce_price_recommendation(
    pricing: AnalysisPricingResponse | None,
    assessment: str,
    damaged_parts: list[str | None],
    recommendation: PriceRecommendation | None,
) -> PriceRecommendation:
    """Keep model advice within the confirmed pricing and assessment boundaries."""
    parts = {part.strip().lower().replace("-", "_").replace(" ", "_") for part in damaged_parts if part}
    missing = []
    if any(not part for part in damaged_parts):
        missing.append("an unidentified damaged part has no exact-match pricing")
    if pricing is None or not parts:
        missing.append("confirmed repair and replacement pricing is unavailable")
    else:
        rows = {row.part_identity: row for row in pricing.line_items}
        for part in sorted(parts):
            for category in ("repair_estimate", "replacement_part_price"):
                row = rows.get(part)
                price = getattr(row, category) if row else None
                expected_type = "REPAIR_ESTIMATE" if category == "repair_estimate" else "REPLACEMENT_PART_PRICE"
                if (price is None or price.status != "FOUND" or price.amount is None
                        or price.currency != "VND" or price.price_type != expected_type):
                    missing.append(f"{part}: {category.replace('_', ' ')}")
        for category in ("repair_estimate", "replacement_part_price"):
            estimate = getattr(pricing, category)
            if (estimate.status != "COMPLETE" or estimate.total_amount is None
                    or estimate.priced_parts != len(parts) or estimate.total_parts != len(parts)):
                missing.append(f"incomplete {category.replace('_', ' ')} coverage")
        if set(rows) != parts:
            missing.append("pricing coverage differs from confirmed damage findings")

    if missing:
        reason = "Missing exact-match price evidence: " + "; ".join(missing)
        return PriceRecommendation(recommendation="MANUAL_REVIEW", rationale=reason[:1100] + ". A human adjuster must verify pricing.")
    allowed = {"REPAIR_LIKELY": "SUPPORTS_REPAIR", "REPLACEMENT_LIKELY": "SUPPORTS_REPLACEMENT"}.get(assessment)
    if recommendation is None:
        return PriceRecommendation(recommendation="MANUAL_REVIEW", rationale="AI pricing advice is unavailable. A human adjuster must compare the supplied estimates.")
    if recommendation.recommendation not in (allowed, "MANUAL_REVIEW"):
        return PriceRecommendation(recommendation="MANUAL_REVIEW", rationale="Price advice conflicts with the deterministic damage assessment. A human adjuster must review the available estimates; the assessment remains unchanged.")
    if not qualitative_rationale_is_safe(recommendation.rationale):
        return PriceRecommendation(recommendation="MANUAL_REVIEW", rationale="AI pricing advice contained unsupported amounts or claim decisions. A human adjuster must inspect the backend estimates; the damage assessment remains unchanged.")
    return recommendation
