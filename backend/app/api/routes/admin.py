from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import AdminUser
from app.core.config import Settings, get_settings
from app.db import get_db
from app.repositories.assessment_rules import AssessmentRuleRepository
from app.schemas.admin import (
    AssessmentRuleChangeResponse,
    AssessmentRuleConfigurationResponse,
    AssessmentRuleValuesSchema,
)
from app.services.assessment_rules import AssessmentRuleService
from app.repositories.vehicle_manufacturers import VehicleManufacturerRepository
from app.schemas.vehicle_makes import (
    VehicleManufacturerResponse,
    VehicleManufacturerUpdateRequest,
    VehicleManufacturerWriteRequest,
)
from app.services.vehicle_manufacturers import VehicleManufacturerService

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_assessment_rule_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AssessmentRuleService:
    return AssessmentRuleService(AssessmentRuleRepository(session), settings)


AssessmentRuleServiceDependency = Annotated[
    AssessmentRuleService, Depends(get_assessment_rule_service)
]


def get_vehicle_manufacturer_service(
    session: Annotated[Session, Depends(get_db)],
) -> VehicleManufacturerService:
    return VehicleManufacturerService(VehicleManufacturerRepository(session))


VehicleManufacturerServiceDependency = Annotated[
    VehicleManufacturerService, Depends(get_vehicle_manufacturer_service)
]


@router.get("/access-check")
def admin_access_check(current_user: AdminUser) -> dict[str, str]:
    return {"status": "ok", "role": current_user.role.value}


@router.get("/assessment-rules", response_model=AssessmentRuleConfigurationResponse)
def get_assessment_rules(
    _current_user: AdminUser,
    service: AssessmentRuleServiceDependency,
) -> AssessmentRuleConfigurationResponse:
    return service.configuration_response()


@router.put("/assessment-rules", response_model=AssessmentRuleConfigurationResponse)
def update_assessment_rules(
    request: AssessmentRuleValuesSchema,
    current_user: AdminUser,
    service: AssessmentRuleServiceDependency,
) -> AssessmentRuleConfigurationResponse:
    return service.update_response(request, current_user)


@router.get("/assessment-rules/history", response_model=list[AssessmentRuleChangeResponse])
def get_assessment_rule_history(
    response: Response,
    _current_user: AdminUser,
    service: AssessmentRuleServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AssessmentRuleChangeResponse]:
    items, total = service.change_responses(page=page, page_size=page_size)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str((total + page_size - 1) // page_size)
    return items


@router.get("/vehicle-makes", response_model=list[VehicleManufacturerResponse])
def list_vehicle_manufacturers(
    response: Response,
    _current_user: AdminUser,
    service: VehicleManufacturerServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[VehicleManufacturerResponse]:
    items, total = service.page_responses(
        page=page, page_size=page_size, active_only=False
    )
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str((total + page_size - 1) // page_size)
    return items


@router.post("/vehicle-makes", response_model=VehicleManufacturerResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle_manufacturer(
    request: VehicleManufacturerWriteRequest,
    _current_user: AdminUser,
    service: VehicleManufacturerServiceDependency,
) -> VehicleManufacturerResponse:
    try:
        return service.create_response(request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.put("/vehicle-makes/{manufacturer_id}", response_model=VehicleManufacturerResponse)
def update_vehicle_manufacturer(
    manufacturer_id: int,
    request: VehicleManufacturerUpdateRequest,
    _current_user: AdminUser,
    service: VehicleManufacturerServiceDependency,
) -> VehicleManufacturerResponse:
    try:
        manufacturer = service.update_response(manufacturer_id, request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if manufacturer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle manufacturer not found")
    return manufacturer
