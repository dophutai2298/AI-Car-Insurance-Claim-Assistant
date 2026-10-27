from dataclasses import dataclass
import logging
from datetime import datetime, timezone
from typing import Protocol
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import DamageAssessment, ReferencePriceStatus, VehiclePartPriceCatalog
from app.services.price_catalog import PRICE_CATEGORIES
from app.services.damage_model import DamageModelDetection

logger = logging.getLogger(__name__)


class PartSearchUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class PartPriceRequest:
    part_identity: str
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    price_type: str = "REPLACEMENT_PART_PRICE"


@dataclass(frozen=True)
class ReferencePartPriceResult:
    part_identity: str
    amount: int | float | None
    currency: str | None
    source_name: str | None
    source_url: str | None
    price_type: str
    retrieved_at: datetime
    status: ReferencePriceStatus
    failure_reason: str | None = None
    effective_at: datetime | None = None
    catalog_id: int | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_year: int | None = None
    unavailable_reason: str | None = None

    def snapshot(self) -> dict:
        return {
            "part_identity": self.part_identity, "price_type": self.price_type,
            "amount": self.amount, "currency": self.currency,
            "source_name": self.source_name, "source_url": self.source_url,
            "status": self.status.value, "failure_reason": self.failure_reason,
            "retrieved_at": self.retrieved_at.isoformat(),
            "effective_at": self.effective_at.isoformat() if self.effective_at else None,
            "catalog_id": self.catalog_id, "vehicle_make": self.vehicle_make,
            "vehicle_model": self.vehicle_model, "vehicle_year": self.vehicle_year,
            "unavailable_reason": self.unavailable_reason,
        }

    @classmethod
    def from_snapshot(cls, payload: dict) -> "ReferencePartPriceResult":
        return cls(**{**payload, "status": ReferencePriceStatus(payload["status"]),
                      "retrieved_at": datetime.fromisoformat(payload["retrieved_at"]),
                      "effective_at": datetime.fromisoformat(payload["effective_at"]) if payload.get("effective_at") else None})


class PartPriceProvider(Protocol):
    def lookup(self, request: PartPriceRequest) -> ReferencePartPriceResult: ...


class CatalogPartPriceProvider:
    def __init__(self, session: Session):
        self.session = session

    def lookup(self, request: PartPriceRequest) -> ReferencePartPriceResult:
        price = self.session.scalar(select(VehiclePartPriceCatalog).where(
            VehiclePartPriceCatalog.vehicle_make == request.vehicle_make,
            VehiclePartPriceCatalog.vehicle_model == request.vehicle_model,
            VehiclePartPriceCatalog.vehicle_year == request.vehicle_year,
            VehiclePartPriceCatalog.part_identity == request.part_identity,
            VehiclePartPriceCatalog.price_type == request.price_type,
        ))
        if price is not None and not 0 <= price.amount <= 1_000_000_000_000:
            raise PartSearchUnavailableError("Catalog amount exceeds the supported VND range")
        return ReferencePartPriceResult(
            part_identity=request.part_identity,
            amount=price.amount if price else None, currency="VND",
            source_name=price.source_name if price else None,
            source_url=price.source_url if price else None,
            price_type=request.price_type,
            retrieved_at=price.retrieved_at if price else datetime.now(timezone.utc),
            effective_at=price.effective_at if price else None,
            catalog_id=price.id if price else None,
            vehicle_make=request.vehicle_make, vehicle_model=request.vehicle_model,
            vehicle_year=request.vehicle_year,
            status=ReferencePriceStatus.FOUND if price else ReferencePriceStatus.UNAVAILABLE,
            failure_reason=None if price else "No exact catalog match",
            unavailable_reason=None if price else "NO_EXACT_MATCH",
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
        parts = sorted({detection.vehicle_part.strip().lower().replace("-", "_").replace(" ", "_")
                        for detection in detections if detection.vehicle_part})
        return [
            self._lookup_part(
                PartPriceRequest(
                    part_identity=part,
                    vehicle_make=vehicle_make,
                    vehicle_model=vehicle_model,
                    vehicle_year=vehicle_year,
                    price_type=category,
                )
            )
            for part in parts
            for category in PRICE_CATEGORIES
        ]

    def _lookup_part(self, request: PartPriceRequest) -> ReferencePartPriceResult:
        try:
            return self.provider.lookup(request)
        except Exception:
            logger.exception("Reference part price lookup failed for %s", request.part_identity)
            return ReferencePartPriceResult(
                part_identity=request.part_identity,
                amount=None,
                currency="VND",
                source_name=None,
                source_url=None,
                price_type=request.price_type,
                retrieved_at=datetime.now(timezone.utc),
                status=ReferencePriceStatus.UNAVAILABLE,
                failure_reason="Reference part price lookup unavailable",
                unavailable_reason="PROVIDER_UNAVAILABLE",
                vehicle_make=request.vehicle_make,
                vehicle_model=request.vehicle_model,
                vehicle_year=request.vehicle_year,
            )


def get_part_price_provider(settings: Settings, session: Session) -> PartPriceProvider:
    return CatalogPartPriceProvider(session) if settings.part_search_mode == "mock" else UnavailablePartPriceProvider()
