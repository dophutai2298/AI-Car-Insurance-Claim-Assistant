"""Create a stable set of demo claims for the dashboard.

Run from the backend directory:
    .venv\Scripts\python.exe scripts\seed_dashboard_claims.py

The script is idempotent. It creates or updates exactly 20 claims identified
by the DEMO_VIN_PREFIX, so rerunning it does not add duplicate dashboard rows.
"""

import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db import Base, create_database_engine, create_session_factory
from app.models import Claim, ClaimStatus, User, UserRole
from app.services.auth import seed_demo_users
from app.services.vehicle_manufacturers import seed_vehicle_manufacturers

DEMO_VIN_PREFIX = "DASHBOARD-DEMO-"


@dataclass(frozen=True)
class DemoClaim:
    claimant_name: str
    make: str
    model: str
    year: int
    status: ClaimStatus


DEMO_CLAIMS: tuple[DemoClaim, ...] = (
    DemoClaim("Nguyen Minh Anh", "Toyota", "Camry", 2023, ClaimStatus.DRAFT),
    DemoClaim("Tran Quoc Bao", "Honda", "CR-V", 2022, ClaimStatus.DRAFT),
    DemoClaim("Le Thu Ha", "VinFast", "VF 8", 2024, ClaimStatus.DRAFT),
    DemoClaim("Pham Gia Huy", "Mazda", "CX-5", 2021, ClaimStatus.DRAFT),
    DemoClaim("Vo Thanh Lam", "Hyundai", "Tucson", 2023, ClaimStatus.ANALYZING),
    DemoClaim("Do Khanh Linh", "Kia", "Seltos", 2022, ClaimStatus.ANALYZING),
    DemoClaim("Bui Tuan Minh", "Ford", "Ranger", 2024, ClaimStatus.ANALYZING),
    DemoClaim("Hoang Yen Nhi", "Toyota", "Corolla Cross", 2023, ClaimStatus.REVIEW_REQUIRED),
    DemoClaim("Dang Duc Phuc", "Honda", "City", 2021, ClaimStatus.REVIEW_REQUIRED),
    DemoClaim("Nguyen Phuong Thao", "VinFast", "VF 5", 2024, ClaimStatus.REVIEW_REQUIRED),
    DemoClaim("Mai Hoai Nam", "Mazda", "Mazda3", 2022, ClaimStatus.REVIEW_REQUIRED),
    DemoClaim("Phan Bao Tram", "Hyundai", "Santa Fe", 2023, ClaimStatus.AI_APPROVED),
    DemoClaim("Truong Minh Khoa", "Kia", "Sportage", 2024, ClaimStatus.AI_APPROVED),
    DemoClaim("Nguyen Thanh Vy", "Ford", "Everest", 2022, ClaimStatus.AI_APPROVED),
    DemoClaim("Le Quang Hieu", "Toyota", "Vios", 2021, ClaimStatus.AI_REJECTED),
    DemoClaim("Pham Ngoc Han", "Honda", "Civic", 2023, ClaimStatus.AI_REJECTED),
    DemoClaim("Bui Duc Long", "VinFast", "VF 9", 2024, ClaimStatus.AI_REJECTED),
    DemoClaim("Vo Thanh Truc", "Mazda", "CX-30", 2022, ClaimStatus.FAILED),
    DemoClaim("Do Tuan Kiet", "Hyundai", "Creta", 2023, ClaimStatus.FAILED),
    DemoClaim("Hoang Mai Anh", "Kia", "Sonet", 2024, ClaimStatus.FAILED),
)


def main() -> None:
    settings = get_settings()
    engine = create_database_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            seed_demo_users(session, settings)
            seed_vehicle_manufacturers(session)
            creator = session.scalar(
                select(User)
                .where(User.role == UserRole.ADMIN)
                .order_by(User.id)
                .limit(1)
            )
            if creator is None:
                raise RuntimeError("An admin user is required to seed dashboard claims")

            existing_claims = {
                claim.vin: claim
                for claim in session.scalars(
                    select(Claim).where(Claim.vin.like(f"{DEMO_VIN_PREFIX}%"))
                )
                if claim.vin
            }
            now = datetime.now(timezone.utc)
            created = 0
            updated = 0

            for index, demo_claim in enumerate(DEMO_CLAIMS, start=1):
                vin = f"{DEMO_VIN_PREFIX}{index:04d}"
                timestamp = now - timedelta(hours=(len(DEMO_CLAIMS) - index) * 3)
                claim = existing_claims.get(vin)

                if claim is None:
                    claim = Claim(
                        claimant_name=demo_claim.claimant_name,
                        vehicle_make=demo_claim.make,
                        vehicle_model=demo_claim.model,
                        vehicle_year=demo_claim.year,
                        license_plate=f"DEMO-{index:03d}",
                        vin=vin,
                        status=demo_claim.status,
                        created_by_user_id=creator.id,
                        created_at=timestamp,
                        updated_at=timestamp,
                    )
                    session.add(claim)
                    session.flush()
                    claim.claim_number = f"CLM-{claim.id:06d}"
                    created += 1
                    continue

                claim.claimant_name = demo_claim.claimant_name
                claim.vehicle_make = demo_claim.make
                claim.vehicle_model = demo_claim.model
                claim.vehicle_year = demo_claim.year
                claim.license_plate = f"DEMO-{index:03d}"
                claim.status = demo_claim.status
                claim.updated_at = timestamp
                updated += 1

            session.commit()
            counts = Counter(demo_claim.status.value for demo_claim in DEMO_CLAIMS)
            print(f"Dashboard demo claims: {created} created, {updated} updated")
            for status in ClaimStatus:
                print(f"{status.value}: {counts[status.value]}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
