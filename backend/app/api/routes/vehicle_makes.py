from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db import get_db
from app.repositories.vehicle_manufacturers import VehicleManufacturerRepository
from app.schemas.vehicle_makes import VehicleManufacturerResponse
from app.services.vehicle_manufacturers import VehicleManufacturerService

router = APIRouter(prefix="/api/vehicle-makes", tags=["claims"])


def get_vehicle_manufacturer_service(
    session: Annotated[Session, Depends(get_db)],
) -> VehicleManufacturerService:
    return VehicleManufacturerService(VehicleManufacturerRepository(session))


VehicleManufacturerServiceDependency = Annotated[
    VehicleManufacturerService, Depends(get_vehicle_manufacturer_service)
]


@router.get("", response_model=list[VehicleManufacturerResponse])
def list_active_vehicle_manufacturers(
    _current_user: CurrentUser,
    service: VehicleManufacturerServiceDependency,
) -> list[VehicleManufacturerResponse]:
    return service.active_responses()
