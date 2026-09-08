from dataclasses import dataclass

from app.core.config import Settings
from app.models import DamageAssessment
from app.services.damage_model import DamageModelDetection

REPLACEMENT_DAMAGE_TYPES = frozenset({"broken_component", "severe_deformation"})


@dataclass(frozen=True)
class AssessmentResult:
    assessment: DamageAssessment
    warning: str | None = None


class DamageAssessmentService:
    def __init__(self, settings: Settings):
        self.confidence_threshold = settings.damage_confidence_threshold
        self.repair_max_percentage = settings.damage_repair_max_percentage
        self.replacement_min_percentage = settings.damage_replacement_min_percentage

    def assess(self, detections: list[DamageModelDetection]) -> AssessmentResult:
        if not detections:
            return AssessmentResult(DamageAssessment.NO_DAMAGE, "No significant vehicle damage was detected in the submitted images. Review manually or request another image; this does not guarantee the vehicle is undamaged.")
        if any(item.confidence < self.confidence_threshold for item in detections):
            return AssessmentResult(DamageAssessment.MANUAL_INSPECTION_REQUIRED, "At least one detection is below the configured confidence threshold. Manual inspection is required.")
        if any(item.damage_type in REPLACEMENT_DAMAGE_TYPES or item.damage_percentage >= self.replacement_min_percentage for item in detections):
            return AssessmentResult(DamageAssessment.REPLACEMENT_LIKELY)
        if all(item.damage_percentage <= self.repair_max_percentage for item in detections):
            return AssessmentResult(DamageAssessment.REPAIR_LIKELY)
        return AssessmentResult(DamageAssessment.MANUAL_INSPECTION_REQUIRED, "Detected damage falls between the configured repair and replacement thresholds. Manual inspection is required.")
