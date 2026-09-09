from dataclasses import dataclass


@dataclass(frozen=True)
class AssessmentRuleValues:
    confidence_threshold: float
    repair_max_percentage: float
    replacement_min_percentage: float
