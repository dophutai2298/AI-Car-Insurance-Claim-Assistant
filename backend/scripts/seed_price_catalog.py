"""Seed editable mock VND prices. Run from backend: python scripts/seed_price_catalog.py.

Examples:
    python scripts/seed_price_catalog.py --dry-run
    python scripts/seed_price_catalog.py --make Toyota --start-year 2020 --end-year 2026
    python scripts/seed_price_catalog.py --update-existing

Generated combinations are demo data, not a historical vehicle production list.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import create_database_engine, create_session_factory
from app.models import VehiclePartPriceCatalog
from app.services.price_catalog import PRICE_CATEGORIES

# Each number is a percentage of PART_PRICES_VND, e.g. 200 means twice the base price.
VEHICLES = {
    "Toyota": {"Camry": 100, "Vios": 80, "Innova": 100, "Fortuner": 120, "Corolla Cross": 110, "Yaris Cross": 95},
    "Honda": {"City": 85, "Civic": 110, "CR-V": 130, "HR-V": 105, "BR-V": 95},
    "Ford": {"Ranger": 120, "Everest": 140, "Explorer": 180, "Territory": 110},
    "Mazda": {"Mazda2": 80, "Mazda3": 100, "Mazda6": 115, "CX-3": 95, "CX-30": 110, "CX-5": 120, "CX-8": 140},
    "Hyundai": {"Accent": 75, "Elantra": 95, "Creta": 90, "Tucson": 110, "Santa Fe": 130, "Grand i10": 65},
    "Kia": {"Morning": 65, "Soluto": 70, "K3": 90, "K5": 110, "Sonet": 85, "Seltos": 95, "Sportage": 115, "Sorento": 130, "Carnival": 145},
    "Mitsubishi": {"Attrage": 75, "Xpander": 90, "Xforce": 100, "Outlander": 120, "Triton": 110, "Pajero Sport": 135},
    "Suzuki": {"Swift": 80, "Ertiga": 85, "XL7": 90, "Jimny": 105},
    "Isuzu": {"D-Max": 110, "mu-X": 125},
    "Nissan": {"Almera": 85, "Kicks": 105, "Navara": 120, "Terra": 130},
    "Mercedes-Benz": {"C200": 200, "C300": 220, "E200": 240, "E300": 260, "GLC 200": 240, "GLC 300": 270},
    "BMW": {"320i": 180, "330i": 200, "520i": 230, "X1": 200, "X3": 240, "X5": 300, "M3": 200},
    "Audi": {"A4": 200, "A6": 250, "Q3": 210, "Q5": 250, "Q7": 300},
    "Lexus": {"ES 250": 250, "NX 350": 280, "RX 350": 320, "LX 600": 400},
    "VinFast": {"Fadil": 75, "Lux A2.0": 120, "Lux SA2.0": 140, "VF e34": 100, "VF 3": 70, "VF 5": 85, "VF 6": 100, "VF 7": 120, "VF 8": 140, "VF 9": 180},
    "Peugeot": {"2008": 120, "3008": 145, "5008": 160, "408": 150},
    "Volkswagen": {"Polo": 110, "T-Cross": 130, "Tiguan": 160, "Teramont": 190},
    "Subaru": {"Forester": 145, "Outback": 170, "Crosstrek": 140},
    "Volvo": {"XC40": 220, "XC60": 260, "XC90": 320, "S90": 260},
}

# part_identity: (repair estimate, replacement part price), whole VND.
# Includes all 21 detector labels plus identifiers used by older analysis runs.
PART_PRICES_VND = {
    "quarter_panel": (2_500_000, 9_000_000),
    "front_wheel": (500_000, 3_000_000),
    "back_window": (400_000, 2_500_000),
    "trunk": (2_000_000, 7_000_000),
    "front_door": (2_400_000, 5_800_000),
    "rocker_panel": (1_500_000, 4_500_000),
    "grille": (600_000, 3_000_000),
    "windshield": (1_200_000, 8_400_000),
    "front_window": (400_000, 2_500_000),
    "back_door": (2_400_000, 5_800_000),
    "headlight": (800_000, 6_000_000),
    "back_wheel": (500_000, 3_000_000),
    "back_windshield": (1_000_000, 5_000_000),
    "hood": (1_900_000, 8_400_000),
    "fender": (2_400_000, 5_800_000),
    "tail_light": (600_000, 3_000_000),
    "license_plate": (100_000, 500_000),
    "front_bumper": (1_900_000, 4_200_000),
    "back_bumper": (1_200_000, 4_200_000),
    "mirror": (500_000, 2_500_000),
    "roof": (3_000_000, 12_000_000),
    "rear_bumper": (1_200_000, 4_200_000),
    "rear_left_door": (2_400_000, 5_800_000),
    "front_left_fender": (3_100_000, 7_300_000),
    "front_left_door": (2_400_000, 5_800_000),
}

# Optional exact prices take precedence over multipliers. Add/edit entries here.
# (make, model, year, part): (repair VND, replacement VND)
PRICE_OVERRIDES: dict[tuple[str, str, int, str], tuple[int, int]] = {
    # ("Toyota", "Camry", 2024, "hood"): (2_000_000, 9_000_000),
}
BASE_YEAR = 2024
YEAR_PRICE_CHANGE_PERCENT = 3
EFFECTIVE_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
SOURCE_NAME = "Demo Vietnam price catalog (mock)"


def build_prices(start_year: int, end_year: int, makes: list[str] | None = None) -> list[dict]:
    if not 1886 <= start_year <= end_year <= 2100:
        raise ValueError("Years must satisfy 1886 <= start-year <= end-year <= 2100")
    selected = makes or list(VEHICLES)
    unknown = set(selected) - VEHICLES.keys()
    if unknown:
        raise ValueError(f"Unknown makes: {', '.join(sorted(unknown))}")
    rows = []
    retrieved_at = datetime.now(timezone.utc)
    for make in dict.fromkeys(selected):
        for model, model_percent in VEHICLES[make].items():
            for year in range(start_year, end_year + 1):
                year_percent = max(60, min(120, 100 + (year - BASE_YEAR) * YEAR_PRICE_CHANGE_PERCENT))
                for part, base_amounts in PART_PRICES_VND.items():
                    amounts = PRICE_OVERRIDES.get((make, model, year, part))
                    if amounts is None:
                        amounts = tuple(amount * model_percent * year_percent // 10_000 for amount in base_amounts)
                    if len(amounts) != 2 or any(type(amount) is not int or not 0 <= amount <= 1_000_000_000_000 for amount in amounts):
                        raise ValueError(f"Invalid VND amounts for {make}/{model}/{year}/{part}")
                    for category, amount in zip(PRICE_CATEGORIES, amounts):
                        rows.append(dict(
                            vehicle_make=make, vehicle_model=model, vehicle_year=year,
                            part_identity=part, price_type=category, amount=amount,
                            source_name=SOURCE_NAME, source_url=None,
                            effective_at=EFFECTIVE_AT, retrieved_at=retrieved_at,
                        ))
    return rows


def save_prices(session: Session, rows: list[dict], update_existing: bool = False) -> tuple[int, int, int]:
    key_columns = ("vehicle_make", "vehicle_model", "vehicle_year", "part_identity", "price_type")
    existing = {
        tuple(getattr(row, column) for column in key_columns): row
        for row in session.scalars(select(VehiclePartPriceCatalog))
    }
    inserted = updated = skipped = 0
    for values in rows:
        key = tuple(values[column] for column in key_columns)
        record = existing.get(key)
        if record is None:
            record = VehiclePartPriceCatalog(**values)
            session.add(record)
            existing[key] = record
            inserted += 1
        elif update_existing:
            for column in ("amount", "source_name", "source_url", "effective_at", "retrieved_at"):
                setattr(record, column, values[column])
            updated += 1
        else:
            skipped += 1
    session.flush()
    return inserted, updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=datetime.now(timezone.utc).year)
    parser.add_argument("--make", action="append", help="Exact make name; repeat to select several makes")
    parser.add_argument("--dry-run", action="store_true", help="Preview generated coverage without connecting to the database")
    parser.add_argument("--update-existing", action="store_true", help="Overwrite matching catalog prices and provenance; existing Analysis snapshots stay unchanged")
    args = parser.parse_args()
    try:
        rows = build_prices(args.start_year, args.end_year, args.make)
    except ValueError as error:
        parser.error(str(error))
    vehicles = {(row["vehicle_make"], row["vehicle_model"]) for row in rows}
    print(f"Mock VND catalog: {len({make for make, _ in vehicles})} makes, {len(vehicles)} models, "
          f"years {args.start_year}-{args.end_year}, {len(PART_PRICES_VND)} parts, {len(rows):,} price records.")
    for make in sorted({make for make, _ in vehicles}):
        print(f"  {make}: {', '.join(sorted(model for brand, model in vehicles if brand == make))}")
    if args.dry_run:
        print("Dry run complete; no database connection or writes.")
        return
    engine = create_database_engine()
    try:
        VehiclePartPriceCatalog.__table__.create(engine, checkfirst=True)
        with create_session_factory(engine)() as session:
            with session.begin():
                inserted, updated, skipped = save_prices(session, rows, args.update_existing)
        print(f"Committed: inserted={inserted:,}, updated={updated:,}, preserved={skipped:,}.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
