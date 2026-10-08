from dataclasses import dataclass


@dataclass(frozen=True)
class AssessmentRuleValues:
    repair_max_percentage: float
    replacement_min_percentage: float
