from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.dependencies import AdminUser
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
    response: Response,
    _current_user: AdminUser,
    service: VehicleManufacturerServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[VehicleManufacturerResponse]:
    items, total = service.page_responses(
        page=page, page_size=page_size, active_only=True
    )
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str((total + page_size - 1) // page_size)
    return items
