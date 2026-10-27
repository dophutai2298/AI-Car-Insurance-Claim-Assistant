from datetime import datetime, timezone
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import VehiclePartPriceCatalog

PRICE_CATEGORIES = ("REPAIR_ESTIMATE", "REPLACEMENT_PART_PRICE")
MAX_SAFE_AMOUNT = 9_007_199_254_740_991


def legacy_reference_prices(prices: list) -> list:
    return [replace(price, price_type="REFERENCE_OEM_PART_PRICE")
            if price.price_type == "REPLACEMENT_PART_PRICE" else price
            for price in prices if price.price_type in ("REPLACEMENT_PART_PRICE", "REFERENCE_OEM_PART_PRICE")]


def seed_price_catalog(session: Session) -> None:
    """Insert demo records without overwriting existing catalog prices."""
    effective = datetime(2026, 1, 1, tzinfo=timezone.utc)
    vehicles = (("Toyota", "Camry", 2022), ("Toyota", "Vios", 2023), ("BMW", "M3", 2024))
    prices = {
        "rear_bumper": (1200000, 4200000),
        "rear_left_door": (2400000, 5800000),
        "front_left_fender": (3100000, 7300000),
        "hood": (1900000, 8400000),
        "front_left_door": (2400000, 5800000),
        "windshield": (1200000, 8400000),
        "fender": (2400000, 5800000),
        "front_bumper": (1900000, 4200000),
    }
    existing_keys = set(session.execute(select(
        VehiclePartPriceCatalog.vehicle_make,
        VehiclePartPriceCatalog.vehicle_model,
        VehiclePartPriceCatalog.vehicle_year,
        VehiclePartPriceCatalog.part_identity,
        VehiclePartPriceCatalog.price_type,
    )))
    for make, model, year in vehicles:
        for part, amounts in prices.items():
            for category, amount in zip(PRICE_CATEGORIES, amounts):
                if (make, model, year, part, category) not in existing_keys:
                    session.add(VehiclePartPriceCatalog(
                        vehicle_make=make, vehicle_model=model, vehicle_year=year,
                        part_identity=part, price_type=category,
                        amount=amount * 2 if make == "BMW" else amount * 4 // 5 if model == "Vios" else amount,
                        source_name="Demo Vietnam price catalog (mock)",
                        source_url=None, effective_at=effective,
                        retrieved_at=datetime.now(timezone.utc),
                    ))
    session.commit()


def pricing_summary(prices: list) -> dict | None:
    """Build estimates only from new VND snapshots; legacy USD prices stay readable."""
    current = [p for p in prices if p.price_type in PRICE_CATEGORIES and p.currency == "VND"]
    if not current:
        return None
    parts = sorted({p.part_identity for p in current})
    result = {"currency": "VND", "line_items": []}
    for category, key in zip(PRICE_CATEGORIES, ("repair_estimate", "replacement_part_price")):
        found = [p for p in current if p.price_type == category and p.status.value == "FOUND" and p.amount is not None]
        subtotal = sum(int(p.amount) for p in found)
        if subtotal > MAX_SAFE_AMOUNT:
            raise ValueError("Price estimate exceeds the supported exact VND range")
        complete = len(found) == len(parts) and bool(parts)
        result[key] = {
            "status": "COMPLETE" if complete else "INCOMPLETE" if found else "UNAVAILABLE",
            "total_amount": subtotal if complete else None,
            "known_subtotal": subtotal, "priced_parts": len(found), "total_parts": len(parts),
        }
    for part in parts:
        result["line_items"].append({
            "part_identity": part,
            **{key: next(p for p in current if p.part_identity == part and p.price_type == category).snapshot()
               for category, key in zip(PRICE_CATEGORIES, ("repair_estimate", "replacement_part_price"))},
        })
    return result
