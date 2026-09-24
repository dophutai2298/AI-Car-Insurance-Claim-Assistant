from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.core.config import Settings
from app.models import DamageDetectionStatus, Evidence


class DamageModelUnavailableError(Exception):
    pass


class DamageType(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    type: str = Field(min_length=1)
    percent: float = Field(ge=0, le=100)


class DamagePart(BaseModel):
    """One item from the damage model's structured JSON response."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    part: str = Field(min_length=1)
    main_damage: str = Field(min_length=1)
    damage_percent: float = Field(ge=0, le=100)
    damage_types: list[DamageType] = Field(min_length=1)
    # Existing assessment rules still use confidence for mock fixtures. The local
    # package does not expose it, so its structured output uses the neutral default.
    assessment_confidence: float = Field(default=1.0, ge=0, le=1, exclude=True)


STRUCTURED_DAMAGE_OUTPUT = TypeAdapter(list[DamagePart])


@dataclass(frozen=True)
class DamageModelDetection:
    source_evidence_id: int
    annotated_evidence_id: int
    vehicle_part: str | None
    damage_type: str | None
    damage_percentage: float
    confidence: float
    status: DamageDetectionStatus


@dataclass(frozen=True)
class DamageModelImageResult:
    source_evidence_id: int
    annotated_evidence_id: int
    parts: tuple[DamagePart, ...]

    @property
    def part_identities(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(part.part for part in self.parts))

    def to_detections(self) -> list[DamageModelDetection]:
        return [
            DamageModelDetection(
                source_evidence_id=self.source_evidence_id,
                annotated_evidence_id=self.annotated_evidence_id,
                vehicle_part=part.part,
                damage_type=part.main_damage,
                damage_percentage=part.damage_percent,
                confidence=part.assessment_confidence,
                status=DamageDetectionStatus.DETECTED,
            )
            for part in self.parts
        ]


@dataclass(frozen=True)
class DamageModelAnalysisResult:
    adapter_name: str
    results: tuple[DamageModelImageResult, ...]
    warnings: tuple[str, ...] = ()

    @property
    def detections(self) -> list[DamageModelDetection]:
        return [detection for result in self.results for detection in result.to_detections()]

    @property
    def part_identities(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                part
                for result in self.results
                for part in result.part_identities
            )
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "part_identities": list(self.part_identities),
            "record": {
                "source_evidence_ids": [result.source_evidence_id for result in self.results],
                "annotated_evidence_ids": [
                    result.annotated_evidence_id for result in self.results
                ],
                "parts": [
                    part.model_dump()
                    for result in self.results
                    for part in result.parts
                ],
            },
        }


class DamageModelAdapter(Protocol):
    def analyze(self, images: list[Evidence]) -> DamageModelAnalysisResult: ...


class EvidencePathResolver(Protocol):
    def resolve_path(self, relative_path: str) -> Path: ...


class DamageCarPackageRunner(Protocol):
    def analyze(self, image_path: Path) -> object: ...


class PendingDamageCarPackageRunner:
    def analyze(self, image_path: Path) -> object:
        # TODO(damage-car): replace this boundary with the package's public inference API.
        raise DamageModelUnavailableError(
            "The local damage_car package API has not been configured yet"
        )


class MockDamageModelAdapter:
    def analyze(self, images: list[Evidence]) -> DamageModelAnalysisResult:
        results: list[DamageModelImageResult] = []
        for image in images:
            fixture_name = image.original_filename.lower()
            if "no-damage" in fixture_name:
                parts: tuple[DamagePart, ...] = ()
            elif "replacement" in fixture_name:
                parts = (self._part("front_left_door", "severe_deformation", 72, 0.92),)
            elif "low-confidence" in fixture_name:
                parts = (self._part("rear_bumper", "scratch", 22, 0.45),)
            elif "multiple" in fixture_name:
                parts = (
                    self._part("rear_bumper", "dent", 32.5, 0.91),
                    self._part("rear_left_door", "scratch", 12.4, 0.88),
                )
            else:
                parts = (self._part("rear_bumper", "dent", 32.5, 0.91),)
            results.append(
                DamageModelImageResult(
                    source_evidence_id=image.id,
                    annotated_evidence_id=image.id,
                    parts=parts,
                )
            )
        return DamageModelAnalysisResult(adapter_name="mock", results=tuple(results))

    @staticmethod
    def _part(
        vehicle_part: str,
        damage_type: str,
        damage_percentage: float,
        confidence: float,
    ) -> DamagePart:
        return DamagePart(
            part=vehicle_part,
            main_damage=damage_type,
            damage_percent=damage_percentage,
            damage_types=[DamageType(type=damage_type, percent=damage_percentage)],
            assessment_confidence=confidence,
        )


class LocalDamageModelAdapter:
    def __init__(
        self,
        storage: EvidencePathResolver,
        runner: DamageCarPackageRunner | None = None,
    ) -> None:
        self.storage = storage
        self.runner = runner or PendingDamageCarPackageRunner()

    def analyze(self, images: list[Evidence]) -> DamageModelAnalysisResult:
        results: list[DamageModelImageResult] = []
        warnings: list[str] = []
        for image in images:
            try:
                image_path = self.storage.resolve_path(image.stored_path)
                parts = tuple(
                    STRUCTURED_DAMAGE_OUTPUT.validate_python(self.runner.analyze(image_path))
                )
                # TODO(damage-car): persist the package's annotated image and use its evidence id.
                results.append(
                    DamageModelImageResult(
                        source_evidence_id=image.id,
                        annotated_evidence_id=image.id,
                        parts=parts,
                    )
                )
            except Exception as error:
                warnings.append(
                    f"Damage model failed for {image.original_filename} ({type(error).__name__})."
                )

        if images and not results:
            raise DamageModelUnavailableError(
                "The local damage model failed for all vehicle images"
            )
        return DamageModelAnalysisResult(
            adapter_name="local",
            results=tuple(results),
            warnings=tuple(warnings),
        )


def get_damage_model_adapter(
    settings: Settings,
    storage: EvidencePathResolver,
) -> DamageModelAdapter:
    if settings.damage_model_mode == "mock":
        return MockDamageModelAdapter()
    return LocalDamageModelAdapter(storage)
