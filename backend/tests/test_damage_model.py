from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.damage_model import (
    DamageModelUnavailableError,
    LocalDamageModelAdapter,
    MockDamageModelAdapter,
    get_damage_model_adapter,
)


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


class FakeRunner:
    def __init__(self, responses: dict[str, list[dict[str, object]] | Exception]) -> None:
        self.responses = responses
        self.calls: list[Path] = []

    def analyze(self, image_path: Path) -> list[dict[str, object]]:
        self.calls.append(image_path)
        response = self.responses[image_path.name]
        if isinstance(response, Exception):
            raise response
        return response


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
    assert result.results[0].annotated_evidence_id == 7
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
    assert output["record"]["annotated_evidence_ids"] == [1, 2]
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


def test_damage_model_factory_selects_mock_or_local_adapter(tmp_path: Path):
    mock_settings = SimpleNamespace(damage_model_mode="mock")
    local_settings = SimpleNamespace(damage_model_mode="local")
    storage = FakeStorage(tmp_path)

    assert isinstance(get_damage_model_adapter(mock_settings, storage), MockDamageModelAdapter)
    assert isinstance(get_damage_model_adapter(local_settings, storage), LocalDamageModelAdapter)
