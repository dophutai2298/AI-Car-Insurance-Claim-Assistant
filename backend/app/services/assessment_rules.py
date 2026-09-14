from app.core.config import Settings
from app.domain.assessment_rules import AssessmentRuleValues
from app.models import AssessmentRuleChange, AssessmentRuleConfiguration, User
from app.repositories.assessment_rules import AssessmentRuleRepository
from app.schemas.admin import (
    AssessmentRuleChangeResponse,
    AssessmentRuleConfigurationResponse,
    AssessmentRuleValuesSchema,
)


class AssessmentRuleService:
    def __init__(self, repository: AssessmentRuleRepository, settings: Settings):
        self.repository = repository
        self.settings = settings

    def active_configuration(self) -> AssessmentRuleConfiguration:
        return self.repository.active() or self.repository.create_initial(self.default_values())

    def active_values(self) -> AssessmentRuleValues:
        return self.repository.values_from_configuration(self.active_configuration())

    def update(self, values: AssessmentRuleValues, changed_by: User) -> AssessmentRuleConfiguration:
        self.active_configuration()
        return self.repository.update(values, changed_by)

    def changes(self) -> list[AssessmentRuleChange]:
        return self.repository.changes()

    def default_values(self) -> AssessmentRuleValues:
        return AssessmentRuleValues(
            confidence_threshold=self.settings.damage_confidence_threshold,
            repair_max_percentage=self.settings.damage_repair_max_percentage,
            replacement_min_percentage=self.settings.damage_replacement_min_percentage,
        )

    def configuration_response(self) -> AssessmentRuleConfigurationResponse:
        configuration = self.active_configuration()
        return AssessmentRuleConfigurationResponse(
            values=self._values_schema(self.repository.values_from_configuration(configuration)),
            updated_by=self.repository.user_email(configuration.updated_by_user_id),
            updated_at=configuration.updated_at,
        )

    def update_response(
        self,
        values: AssessmentRuleValuesSchema,
        changed_by: User,
    ) -> AssessmentRuleConfigurationResponse:
        configuration = self.update(self._values_from_schema(values), changed_by)
        return AssessmentRuleConfigurationResponse(
            values=values,
            updated_by=changed_by.email,
            updated_at=configuration.updated_at,
        )

    def change_responses(self) -> list[AssessmentRuleChangeResponse]:
        return [self._change_response(change) for change in self.changes()]

    @staticmethod
    def _values_from_schema(values: AssessmentRuleValuesSchema) -> AssessmentRuleValues:
        return AssessmentRuleValues(**values.model_dump())

    @staticmethod
    def _values_schema(values: AssessmentRuleValues) -> AssessmentRuleValuesSchema:
        return AssessmentRuleValuesSchema(**values.__dict__)

    def _change_response(self, change: AssessmentRuleChange) -> AssessmentRuleChangeResponse:
        return AssessmentRuleChangeResponse(
            changed_by=self.repository.user_email(change.changed_by_user_id) or "Unknown user",
            changed_at=change.changed_at,
            old_values=AssessmentRuleValuesSchema(
                confidence_threshold=change.old_confidence_threshold,
                repair_max_percentage=change.old_repair_max_percentage,
                replacement_min_percentage=change.old_replacement_min_percentage,
            ),
            new_values=AssessmentRuleValuesSchema(
                confidence_threshold=change.new_confidence_threshold,
                repair_max_percentage=change.new_repair_max_percentage,
                replacement_min_percentage=change.new_replacement_min_percentage,
            ),
        )
