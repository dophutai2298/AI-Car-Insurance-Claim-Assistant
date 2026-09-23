from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import Settings
from app.models import Evidence
from app.services.damage_output import (
    CarDamageRecord,
    DamageDetail,
    DamageModelDetection,
    DamagePart,
    normalize_damage_text,
)


class DamageModelUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class DamageModelAnalysisResult:
    adapter_name: str
    records: tuple[CarDamageRecord, ...]
    warnings: tuple[str, ...] = ()

    @property
    def detections(self) -> list[DamageModelDetection]:
        return [detection for record in self.records for detection in record.to_detections()]

    @property
    def part_identities(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                part
                for record in self.records
                for part in record.part_identities
            )
        )

    def to_dict(self) -> dict[str, object]:
        aggregate_record = {
            "source_evidence_ids": [record.source_evidence_id for record in self.records],
            "annotated_evidence_ids": [
                record.annotated_evidence_id for record in self.records
            ],
            "raw_text": "\n\n".join(
                record.raw_text for record in self.records if record.raw_text
            ),
            "parts": [
                part.to_dict()
                for record in self.records
                for part in record.parts
            ],
        }
        return {
            "part_identities": list(self.part_identities),
            "record": aggregate_record,
        }


class DamageModelAdapter(Protocol):
    def analyze(self, images: list[Evidence]) -> DamageModelAnalysisResult: ...


class EvidencePathResolver(Protocol):
    def resolve_path(self, relative_path: str) -> Path: ...


class DamageCarPackageRunner(Protocol):
    def analyze(self, image_path: Path) -> str: ...


class PendingDamageCarPackageRunner:
    def analyze(self, image_path: Path) -> str:
        # TODO(damage-car): replace this boundary with the package's public inference API.
        raise DamageModelUnavailableError(
            "The local damage_car package API has not been configured yet"
        )


class MockDamageModelAdapter:
    def analyze(self, images: list[Evidence]) -> DamageModelAnalysisResult:
        records: list[CarDamageRecord] = []
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
            raw_text = self._format_raw_text(parts)
            records.append(
                normalize_damage_text(
                    raw_text,
                    source_evidence_id=image.id,
                    annotated_evidence_id=image.id,
                )
            )
        return DamageModelAnalysisResult(adapter_name="mock", records=tuple(records))

    @staticmethod
    def _part(
        vehicle_part: str,
        damage_type: str,
        damage_percentage: float,
        confidence: float,
    ) -> DamagePart:
        return DamagePart(
            vehicle_part=vehicle_part,
            total_damage_percentage=damage_percentage,
            part_confidence=confidence,
            damage_details=(
                DamageDetail(
                    damage_type=damage_type,
                    area_percentage=damage_percentage,
                    pixels=0,
                    confidence=confidence,
                ),
            ),
        )

    @staticmethod
    def _format_raw_text(parts: tuple[DamagePart, ...]) -> str:
        lines: list[str] = []
        for part in parts:
            lines.append(
                f"{part.vehicle_part} | Total Damage: {part.total_damage_percentage:.2f}% "
                f"| Part Conf: {part.part_confidence:.2f}"
            )
            lines.extend(
                f"  - {detail.damage_type} | Area: {detail.area_percentage:.2f}% "
                f"| Pixels: {detail.pixels:,} | Conf: {detail.confidence:.2f}"
                for detail in part.damage_details
            )
        return "\n".join(lines)


class LocalDamageModelAdapter:
    def __init__(
        self,
        storage: EvidencePathResolver,
        runner: DamageCarPackageRunner | None = None,
    ) -> None:
        self.storage = storage
        self.runner = runner or PendingDamageCarPackageRunner()

    def analyze(self, images: list[Evidence]) -> DamageModelAnalysisResult:
        records: list[CarDamageRecord] = []
        warnings: list[str] = []
        for image in images:
            try:
                image_path = self.storage.resolve_path(image.stored_path)
                raw_text = self.runner.analyze(image_path)
                record = normalize_damage_text(
                    raw_text,
                    source_evidence_id=image.id,
                    # TODO(damage-car): persist the package's annotated image and use its evidence id.
                    annotated_evidence_id=image.id,
                )
                if not record.parts:
                    warnings.append(
                        f"No structured damage parts were parsed from {image.original_filename}."
                    )
                records.append(record)
            except Exception as error:
                warnings.append(
                    f"Damage model failed for {image.original_filename} ({type(error).__name__})."
                )

        if images and not records:
            raise DamageModelUnavailableError(
                "The local damage model failed for all vehicle images"
            )
        return DamageModelAnalysisResult(
            adapter_name="local",
            records=tuple(records),
            warnings=tuple(warnings),
        )


def get_damage_model_adapter(
    settings: Settings,
    storage: EvidencePathResolver,
) -> DamageModelAdapter:
    if settings.damage_model_mode == "mock":
        return MockDamageModelAdapter()
    return LocalDamageModelAdapter(storage)
