from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings
from app.models import DamageDetectionStatus, Evidence


class DamageModelUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class DamageModelDetection:
    source_evidence_id: int
    annotated_evidence_id: int
    vehicle_part: str | None
    damage_type: str | None
    damage_percentage: float
    confidence: float
    status: DamageDetectionStatus


class DamageModelAdapter(Protocol):
    def analyze(self, images: list[Evidence]) -> list[DamageModelDetection]: ...


class MockDamageModelAdapter:
    def analyze(self, images: list[Evidence]) -> list[DamageModelDetection]:
        detections: list[DamageModelDetection] = []
        for image in images:
            fixture_name = image.original_filename.lower()
            if "no-damage" in fixture_name:
                continue
            if "replacement" in fixture_name:
                detections.append(self._detection(image, "front_left_door", "severe_deformation", 72, 0.92))
            elif "low-confidence" in fixture_name:
                detections.append(self._detection(image, "rear_bumper", "scratch", 22, 0.45))
            elif "multiple" in fixture_name:
                detections.extend(
                    [
                        self._detection(image, "rear_bumper", "dent", 32.5, 0.91),
                        self._detection(image, "rear_left_door", "scratch", 12.4, 0.88),
                    ]
                )
            else:
                detections.append(self._detection(image, "rear_bumper", "dent", 32.5, 0.91))
        return detections

    @staticmethod
    def _detection(image: Evidence, vehicle_part: str, damage_type: str, damage_percentage: float, confidence: float) -> DamageModelDetection:
        return DamageModelDetection(
            source_evidence_id=image.id,
            annotated_evidence_id=image.id,
            vehicle_part=vehicle_part,
            damage_type=damage_type,
            damage_percentage=damage_percentage,
            confidence=confidence,
            status=DamageDetectionStatus.DETECTED,
        )


class UnavailableDamageModelAdapter:
    def analyze(self, images: list[Evidence]) -> list[DamageModelDetection]:
        raise DamageModelUnavailableError("The configured HTTP damage model adapter is not available in this PoC")


def get_damage_model_adapter(settings: Settings) -> DamageModelAdapter:
    return MockDamageModelAdapter() if settings.damage_model_mode == "mock" else UnavailableDamageModelAdapter()
