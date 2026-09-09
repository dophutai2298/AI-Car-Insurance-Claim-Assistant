from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import VehicleManufacturer


class VehicleManufacturerRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_active(self) -> list[VehicleManufacturer]:
        statement = select(VehicleManufacturer).where(VehicleManufacturer.is_active).order_by(VehicleManufacturer.name)
        return list(self.session.scalars(statement))

    def list_all(self) -> list[VehicleManufacturer]:
        return list(self.session.scalars(select(VehicleManufacturer).order_by(VehicleManufacturer.name)))

    def find_by_id(self, manufacturer_id: int) -> VehicleManufacturer | None:
        return self.session.get(VehicleManufacturer, manufacturer_id)

    def find_by_name(self, name: str) -> VehicleManufacturer | None:
        statement = select(VehicleManufacturer).where(func.lower(VehicleManufacturer.name) == name.lower())
        return self.session.scalar(statement)

    def create(self, name: str) -> VehicleManufacturer:
        manufacturer = VehicleManufacturer(name=name)
        self.session.add(manufacturer)
        self._commit_or_raise_duplicate()
        self.session.refresh(manufacturer)
        return manufacturer

    def update(self, manufacturer: VehicleManufacturer, name: str, is_active: bool) -> VehicleManufacturer:
        manufacturer.name = name
        manufacturer.is_active = is_active
        self._commit_or_raise_duplicate()
        self.session.refresh(manufacturer)
        return manufacturer

    def _commit_or_raise_duplicate(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise ValueError("Vehicle manufacturer already exists") from error
