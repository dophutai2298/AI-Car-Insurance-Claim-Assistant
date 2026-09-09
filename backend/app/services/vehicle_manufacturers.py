from sqlalchemy.orm import Session

from app.models import VehicleManufacturer
from app.repositories.vehicle_manufacturers import VehicleManufacturerRepository
from app.schemas.vehicle_makes import (
    VehicleManufacturerResponse,
    VehicleManufacturerUpdateRequest,
    VehicleManufacturerWriteRequest,
)

INITIAL_VEHICLE_MANUFACTURERS = (
    "Toyota", "Honda", "Ford", "Mazda", "Hyundai", "Kia", "Mitsubishi", "Suzuki", "Isuzu",
    "Nissan", "Mercedes-Benz", "BMW", "Audi", "Lexus", "VinFast", "Peugeot", "Volkswagen",
    "Subaru", "Volvo",
)


class VehicleManufacturerService:
    def __init__(self, repository: VehicleManufacturerRepository):
        self.repository = repository

    def active_responses(self) -> list[VehicleManufacturerResponse]:
        return [VehicleManufacturerResponse.model_validate(item) for item in self.repository.list_active()]

    def all_responses(self) -> list[VehicleManufacturerResponse]:
        return [VehicleManufacturerResponse.model_validate(item) for item in self.repository.list_all()]

    def create_response(self, request: VehicleManufacturerWriteRequest) -> VehicleManufacturerResponse:
        name = request.name.strip()
        if self.repository.find_by_name(name) is not None:
            raise ValueError("Vehicle manufacturer already exists")
        return VehicleManufacturerResponse.model_validate(self.repository.create(name))

    def update_response(
        self, manufacturer_id: int, request: VehicleManufacturerUpdateRequest
    ) -> VehicleManufacturerResponse | None:
        manufacturer = self.repository.find_by_id(manufacturer_id)
        if manufacturer is None:
            return None
        name = request.name.strip()
        existing = self.repository.find_by_name(name)
        if existing is not None and existing.id != manufacturer.id:
            raise ValueError("Vehicle manufacturer already exists")
        return VehicleManufacturerResponse.model_validate(
            self.repository.update(manufacturer, name, request.is_active)
        )

    def is_active_name(self, name: str) -> bool:
        manufacturer = self.repository.find_by_name(name.strip())
        return manufacturer is not None and manufacturer.is_active


def seed_vehicle_manufacturers(session: Session) -> None:
    repository = VehicleManufacturerRepository(session)
    for name in INITIAL_VEHICLE_MANUFACTURERS:
        if repository.find_by_name(name) is None:
            session.add(VehicleManufacturer(name=name))
    session.commit()
