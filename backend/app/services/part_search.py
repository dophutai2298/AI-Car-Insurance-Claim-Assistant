from dataclasses import dataclass
import logging
from datetime import datetime, timezone
from typing import Protocol

from app.core.config import Settings
from app.models import DamageAssessment, ReferencePriceStatus
from app.services.damage_model import DamageModelDetection

REFERENCE_OEM_PART_PRICE = "REFERENCE_OEM_PART_PRICE"
logger = logging.getLogger(__name__)


class PartSearchUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class PartPriceRequest:
    part_identity: str
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int


@dataclass(frozen=True)
class ReferencePartPriceResult:
    part_identity: str
    amount: float | None
    currency: str | None
    source_name: str | None
    source_url: str | None
    price_type: str
    retrieved_at: datetime
    status: ReferencePriceStatus
    failure_reason: str | None = None


class PartPriceProvider(Protocol):
    def lookup(self, request: PartPriceRequest) -> ReferencePartPriceResult: ...


class MockPartPriceProvider:
    _FIXTURES = {
        "front_left_door": 950.0,
        "rear_bumper": 420.0,
        "rear_left_door": 780.0,
    }

    def lookup(self, request: PartPriceRequest) -> ReferencePartPriceResult:
        source_path = request.part_identity.replace("_", "-")
        return ReferencePartPriceResult(
            part_identity=request.part_identity,
            amount=self._FIXTURES.get(request.part_identity, 500.0),
            currency="USD",
            source_name="Mock OEM Parts Catalog",
            source_url=f"https://example.com/oem-parts/{source_path}",
            price_type=REFERENCE_OEM_PART_PRICE,
            retrieved_at=datetime.now(timezone.utc),
            status=ReferencePriceStatus.FOUND,
        )


class UnavailablePartPriceProvider:
    def lookup(self, request: PartPriceRequest) -> ReferencePartPriceResult:
        raise PartSearchUnavailableError("Reference part price provider is unavailable")


class PartSearchService:
    def __init__(self, provider: PartPriceProvider):
        self.provider = provider

    def lookup_for_assessment(
        self,
        assessment: DamageAssessment,
        detections: list[DamageModelDetection],
        vehicle_make: str,
        vehicle_model: str,
        vehicle_year: int,
        force_lookup: bool = False,
    ) -> list[ReferencePartPriceResult]:
        if assessment is not DamageAssessment.REPLACEMENT_LIKELY and not force_lookup:
            return []
        parts = sorted({detection.vehicle_part for detection in detections if detection.vehicle_part})
        return [
            self._lookup_part(
                PartPriceRequest(
                    part_identity=part,
                    vehicle_make=vehicle_make,
                    vehicle_model=vehicle_model,
                    vehicle_year=vehicle_year,
                )
            )
            for part in parts
        ]

    def _lookup_part(self, request: PartPriceRequest) -> ReferencePartPriceResult:
        try:
            return self.provider.lookup(request)
        except Exception:
            logger.exception("Reference part price lookup failed for %s", request.part_identity)
            return ReferencePartPriceResult(
                part_identity=request.part_identity,
                amount=None,
                currency=None,
                source_name=None,
                source_url=None,
                price_type=REFERENCE_OEM_PART_PRICE,
                retrieved_at=datetime.now(timezone.utc),
                status=ReferencePriceStatus.UNAVAILABLE,
                failure_reason="Reference part price lookup unavailable",
            )


def get_part_price_provider(settings: Settings) -> PartPriceProvider:
    return MockPartPriceProvider() if settings.part_search_mode == "mock" else UnavailablePartPriceProvider()
