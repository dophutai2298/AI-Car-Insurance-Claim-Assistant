from typing import Annotated

from fastapi import APIRouter, Depends
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

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_assessment_rule_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AssessmentRuleService:
    return AssessmentRuleService(AssessmentRuleRepository(session), settings)


AssessmentRuleServiceDependency = Annotated[
    AssessmentRuleService, Depends(get_assessment_rule_service)
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
    _current_user: AdminUser,
    service: AssessmentRuleServiceDependency,
) -> list[AssessmentRuleChangeResponse]:
    return service.change_responses()
