from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class AssessmentRuleValuesSchema(BaseModel):
    confidence_threshold: float = Field(ge=0, le=1)
    repair_max_percentage: float = Field(ge=0, le=100)
    replacement_min_percentage: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def repair_threshold_must_precede_replacement_threshold(self):
        if self.repair_max_percentage >= self.replacement_min_percentage:
            raise ValueError(
                "repair_max_percentage must be less than replacement_min_percentage"
            )
        return self


class AssessmentRuleConfigurationResponse(BaseModel):
    values: AssessmentRuleValuesSchema
    updated_by: str | None
    updated_at: datetime


class AssessmentRuleChangeResponse(BaseModel):
    changed_by: str
    changed_at: datetime
    old_values: AssessmentRuleValuesSchema
    new_values: AssessmentRuleValuesSchema
