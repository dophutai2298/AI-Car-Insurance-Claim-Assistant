from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.assessment_rules import AssessmentRuleValues
from app.models import AssessmentRuleChange, AssessmentRuleConfiguration, User


class AssessmentRuleRepository:
    def __init__(self, session: Session):
        self.session = session

    def active(self) -> AssessmentRuleConfiguration | None:
        return self.session.get(AssessmentRuleConfiguration, 1)

    def create_initial(self, values: AssessmentRuleValues) -> AssessmentRuleConfiguration:
        configuration = AssessmentRuleConfiguration(id=1, **values.__dict__)
        self.session.add(configuration)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing_configuration = self.active()
            if existing_configuration is not None:
                return existing_configuration
            raise
        self.session.refresh(configuration)
        return configuration

    def update(
        self,
        values: AssessmentRuleValues,
        changed_by: User,
    ) -> AssessmentRuleConfiguration:
        configuration = self.session.scalar(
            select(AssessmentRuleConfiguration)
            .where(AssessmentRuleConfiguration.id == 1)
            .with_for_update()
        )
        if configuration is None:
            raise ValueError("Assessment rules must be initialized before updating")
        previous_values = self.values_from_configuration(configuration)
        self.session.add(
            AssessmentRuleChange(
                changed_by_user_id=changed_by.id,
                old_confidence_threshold=previous_values.confidence_threshold,
                old_repair_max_percentage=previous_values.repair_max_percentage,
                old_replacement_min_percentage=previous_values.replacement_min_percentage,
                new_confidence_threshold=values.confidence_threshold,
                new_repair_max_percentage=values.repair_max_percentage,
                new_replacement_min_percentage=values.replacement_min_percentage,
            )
        )
        configuration.confidence_threshold = values.confidence_threshold
        configuration.repair_max_percentage = values.repair_max_percentage
        configuration.replacement_min_percentage = values.replacement_min_percentage
        configuration.updated_by_user_id = changed_by.id
        self.session.commit()
        self.session.refresh(configuration)
        return configuration

    def changes(self) -> list[AssessmentRuleChange]:
        statement = select(AssessmentRuleChange).order_by(AssessmentRuleChange.changed_at.desc())
        return list(self.session.scalars(statement))

    def user_email(self, user_id: int | None) -> str | None:
        return self.session.scalar(select(User.email).where(User.id == user_id)) if user_id else None

    @staticmethod
    def values_from_configuration(configuration: AssessmentRuleConfiguration) -> AssessmentRuleValues:
        return AssessmentRuleValues(
            confidence_threshold=configuration.confidence_threshold,
            repair_max_percentage=configuration.repair_max_percentage,
            replacement_min_percentage=configuration.replacement_min_percentage,
        )
