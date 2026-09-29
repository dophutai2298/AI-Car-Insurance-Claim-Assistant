from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.damage_model import (
    CarDamageDetectorRunner,
    DamageModelUnavailableError,
    LocalDamageModelAdapter,
    get_damage_model_adapter,
)
from app.services.evidence_storage import StoredEvidence
from app.services import damage_model


MODEL_OUTPUT = [
    {
        "part": "Door",
        "main_damage": "dent",
        "damage_percent": 42.5,
        "damage_types": [{"type": "dent", "percent": 42.5}],
    }
]


class FakeStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def resolve_path(self, relative_path: str) -> Path:
        return self.root / relative_path

    def save_annotation(self, claim_number: str, image_bytes: bytes, filename: str) -> StoredEvidence:
        return StoredEvidence(f"{claim_number}/annotated.jpg", "annotated.jpg", "image/jpeg", 8)

    def delete_stored(self, uploads):
        pass


class FakeRunner:
    def __init__(self, responses: dict[str, list[dict[str, object]] | Exception]) -> None:
        self.responses = responses
        self.calls: list[Path] = []

    def predict(self, image_path: Path) -> tuple[bytes, list[dict[str, object]]]:
        self.calls.append(image_path)
        response = self.responses[image_path.name]
        if isinstance(response, Exception):
            raise response
        return b"\xff\xd8\xffannotation", response


def evidence(evidence_id: int, filename: str):
    return SimpleNamespace(id=evidence_id, original_filename=filename, stored_path=filename)


def test_local_adapter_resolves_images_and_accepts_structured_package_output(tmp_path: Path):
    runner = FakeRunner({"damage.jpg": MODEL_OUTPUT})
    adapter = LocalDamageModelAdapter(FakeStorage(tmp_path), runner)

    result = adapter.analyze([evidence(7, "damage.jpg")])

    assert runner.calls == [tmp_path / "damage.jpg"]
    assert result.adapter_name == "local"
    assert result.part_identities == ("Door",)
    assert result.warnings == ()
    assert result.results[0].source_evidence_id == 7
    assert result.results[0].annotated_evidence_id is None
    assert result.results[0].annotation is not None
    assert result.results[0].parts[0].model_dump() == MODEL_OUTPUT[0]
    assert result.detections[0].vehicle_part == "Door"
    assert result.detections[0].damage_type == "dent"
    assert result.detections[0].damage_percentage == 42.5


def test_local_adapter_isolates_one_image_failure_when_another_image_succeeds(tmp_path: Path):
    runner = FakeRunner(
        {"failed.jpg": RuntimeError("model could not read image"), "working.jpg": MODEL_OUTPUT}
    )
    adapter = LocalDamageModelAdapter(FakeStorage(tmp_path), runner)

    result = adapter.analyze([evidence(1, "failed.jpg"), evidence(2, "working.jpg")])

    assert len(result.results) == 1
    assert result.results[0].source_evidence_id == 2
    assert len(result.warnings) == 1
    assert "failed.jpg" in result.warnings[0]


def test_analysis_result_exposes_one_aggregate_record_for_multiple_images(tmp_path: Path):
    runner = FakeRunner({"first.jpg": MODEL_OUTPUT, "second.jpg": MODEL_OUTPUT})
    adapter = LocalDamageModelAdapter(FakeStorage(tmp_path), runner)

    result = adapter.analyze([evidence(1, "first.jpg"), evidence(2, "second.jpg")])

    output = result.to_dict()
    assert output["record"]["source_evidence_ids"] == [1, 2]
    assert output["record"]["annotated_evidence_ids"] == [None, None]
    assert len(output["record"]["parts"]) == 2
    assert output["record"]["parts"][0] == MODEL_OUTPUT[0]
    assert "raw_text" not in output["record"]


def test_local_adapter_rejects_malformed_structured_output(tmp_path: Path):
    adapter = LocalDamageModelAdapter(
        FakeStorage(tmp_path),
        FakeRunner(
            {
                "invalid.jpg": [
                    {
                        "part": "Door",
                        "main_damage": "dent",
                        "damage_percent": 142.5,
                        "damage_types": [{"type": "dent", "percent": 42.5}],
                    }
                ]
            }
        ),
    )

    with pytest.raises(DamageModelUnavailableError, match="all vehicle images"):
        adapter.analyze([evidence(1, "invalid.jpg")])


def test_local_adapter_reports_unavailable_when_all_images_fail(tmp_path: Path):
    adapter = LocalDamageModelAdapter(
        FakeStorage(tmp_path), FakeRunner({"failed.jpg": RuntimeError("package unavailable")})
    )

    with pytest.raises(DamageModelUnavailableError, match="all vehicle images"):
        adapter.analyze([evidence(1, "failed.jpg")])


def test_damage_model_factory_always_uses_local_detector(tmp_path: Path):
    local_settings = SimpleNamespace()
    storage = FakeStorage(tmp_path)

    adapter = get_damage_model_adapter(local_settings, storage)
    assert isinstance(adapter, LocalDamageModelAdapter)
    assert isinstance(adapter.runner, CarDamageDetectorRunner)


def test_runner_passes_config_to_detector_and_returns_saved_image_bytes(tmp_path: Path, monkeypatch):
    image = tmp_path / "damage.jpg"
    image.write_bytes(b"image")
    settings = SimpleNamespace(
        damage_output_dir=str(tmp_path / "results"),
        damage_part_model_path=str(tmp_path / "parts.pt"),
        damage_model_path=str(tmp_path / "damage.pt"),
        damage_part_conf=0.25,
        damage_damage_conf=0.15,
        damage_min_percent=3.0,
        damage_image_size=640,
        damage_device="cpu",
        project_path=lambda value: Path(value),
    )
    calls = []

    class Detector:
        def predict(self, path):
            calls.append(path)
            result_dir = Path(settings.damage_output_dir)
            result_dir.mkdir()
            (result_dir / "damage_result.jpg").write_bytes(b"\xff\xd8\xffannotated")
            return object(), MODEL_OUTPUT

    monkeypatch.setattr(damage_model, "_load_detector", lambda *args: Detector())

    annotated, parts = CarDamageDetectorRunner(settings).predict(image)

    assert calls == [str(image)]
    assert annotated == b"\xff\xd8\xffannotated"
    assert parts == MODEL_OUTPUT


def test_runner_rejects_missing_image_before_loading_model(tmp_path: Path):
    with pytest.raises(DamageModelUnavailableError, match="image is missing"):
        CarDamageDetectorRunner(SimpleNamespace()).predict(tmp_path / "missing.jpg")


def test_detector_loader_rejects_missing_weights(tmp_path: Path):
    with pytest.raises(DamageModelUnavailableError, match="weights are missing"):
        damage_model._load_detector(
            str(tmp_path / "missing-part.pt"), str(tmp_path / "missing-damage.pt"),
            str(tmp_path / "results"), 0.25, 0.15, 3.0, 640, "cpu",
        )
