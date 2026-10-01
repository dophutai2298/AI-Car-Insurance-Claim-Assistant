from dataclasses import dataclass
from functools import lru_cache
import importlib.util
import logging
from pathlib import Path
from threading import Lock
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.core.config import Settings
from app.models import DamageDetectionStatus, Evidence
from app.services.evidence_storage import StoredEvidence

logger = logging.getLogger(__name__)


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
    annotated_evidence_id: int | None
    parts: tuple[DamagePart, ...]
    annotation: StoredEvidence | None = None

    @property
    def part_identities(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(part.part for part in self.parts))

    def to_detections(self) -> list[DamageModelDetection]:
        return [
            DamageModelDetection(
                source_evidence_id=self.source_evidence_id,
                annotated_evidence_id=self.annotated_evidence_id or self.source_evidence_id,
                vehicle_part=part.part,
                damage_type=part.main_damage,
                damage_percentage=part.damage_percent,
                confidence=1.0,
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
    def annotations(self) -> list[StoredEvidence]:
        return [result.annotation for result in self.results if result.annotation is not None]

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

    def save_annotation(self, claim_number: str, image_bytes: bytes, filename: str) -> StoredEvidence: ...

    def delete_stored(self, uploads: list[StoredEvidence]) -> None: ...


class DamageCarPackageRunner(Protocol):
    def predict(self, image_path: Path) -> tuple[bytes, object]: ...


@lru_cache(maxsize=4)
def _load_detector(
    part_model: str,
    damage_model: str,
    output_dir: str,
    part_conf: float,
    damage_conf: float,
    min_percent: float,
    image_size: int,
    device: str,
):
    module_path = Settings.project_path("AI/car_damage_detector.py")
    if not all(path.is_file() for path in (module_path, Path(part_model), Path(damage_model))):
        raise DamageModelUnavailableError("Car damage detector or model weights are missing")
    spec = importlib.util.spec_from_file_location("car_damage_detector", module_path)
    if spec is None or spec.loader is None:
        raise DamageModelUnavailableError("Car damage detector could not be imported")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CarDamageDetector(
        part_model_path=part_model,
        damage_model_path=damage_model,
        output_dir=output_dir,
        part_conf=part_conf,
        damage_conf=damage_conf,
        min_damage_percent=min_percent,
        imgsz=image_size,
        device=device,
    )


_detector_lock = Lock()


class CarDamageDetectorRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def predict(self, image_path: Path) -> tuple[bytes, object]:
        if not image_path.is_file():
            raise DamageModelUnavailableError("Vehicle damage image is missing")
        settings = self.settings
        output_dir = settings.project_path(settings.damage_output_dir)
        with _detector_lock:
            detector = _load_detector(
                str(settings.project_path(settings.damage_part_model_path)),
                str(settings.project_path(settings.damage_model_path)),
                str(output_dir),
                settings.damage_part_conf,
                settings.damage_damage_conf,
                settings.damage_min_percent,
                settings.damage_image_size,
                settings.damage_device,
            )
            _, parts = detector.predict(str(image_path))
            annotated_path = output_dir / f"{image_path.stem}_result.jpg"
            if not annotated_path.is_file():
                raise DamageModelUnavailableError("Detector did not save an annotated image")
            return annotated_path.read_bytes(), parts


class LocalDamageModelAdapter:
    def __init__(
        self,
        storage: EvidencePathResolver,
        runner: DamageCarPackageRunner,
    ) -> None:
        self.storage = storage
        self.runner = runner

    def analyze(self, images: list[Evidence]) -> DamageModelAnalysisResult:
        results: list[DamageModelImageResult] = []
        warnings: list[str] = []
        for image in images:
            try:
                image_path = self.storage.resolve_path(image.stored_path)
                annotated_bytes, raw_parts = self.runner.predict(image_path)
                parts = tuple(
                    STRUCTURED_DAMAGE_OUTPUT.validate_python(raw_parts)
                )
                annotation = self.storage.save_annotation(
                    image.stored_path.split("/", 1)[0], annotated_bytes, image.original_filename
                )
                results.append(
                    DamageModelImageResult(
                        source_evidence_id=image.id,
                        annotated_evidence_id=None,
                        parts=parts,
                        annotation=annotation,
                    )
                )
            except Exception as error:
                logger.warning("Damage detector failed for evidence %s", image.id, exc_info=True)
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
    return LocalDamageModelAdapter(storage, CarDamageDetectorRunner(settings))
