from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.damage_model import (
    DamageModelUnavailableError,
    LocalDamageModelAdapter,
    MockDamageModelAdapter,
    get_damage_model_adapter,
)


RAW_TEXT = """
Door | Total Damage: 42.50% | Part Conf: 0.91
  └─ dent | Area: 42.50% | Pixels: 1,200 | Conf: 0.84
"""


class FakeStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def resolve_path(self, relative_path: str) -> Path:
        return self.root / relative_path


class FakeRunner:
    def __init__(self, responses: dict[str, str | Exception]) -> None:
        self.responses = responses
        self.calls: list[Path] = []

    def analyze(self, image_path: Path) -> str:
        self.calls.append(image_path)
        response = self.responses[image_path.name]
        if isinstance(response, Exception):
            raise response
        return response


def evidence(evidence_id: int, filename: str):
    return SimpleNamespace(
        id=evidence_id,
        original_filename=filename,
        stored_path=filename,
    )


def test_local_adapter_resolves_images_and_normalizes_package_raw_text(tmp_path: Path):
    runner = FakeRunner({"damage.jpg": RAW_TEXT})
    adapter = LocalDamageModelAdapter(FakeStorage(tmp_path), runner)

    result = adapter.analyze([evidence(7, "damage.jpg")])

    assert runner.calls == [tmp_path / "damage.jpg"]
    assert result.adapter_name == "local"
    assert result.part_identities == ("Door",)
    assert result.warnings == ()
    assert result.records[0].raw_text == RAW_TEXT
    assert result.records[0].source_evidence_id == 7
    assert result.records[0].annotated_evidence_id == 7
    assert result.detections[0].vehicle_part == "Door"
    assert result.detections[0].damage_percentage == 42.5


def test_local_adapter_isolates_one_image_failure_when_another_image_succeeds(tmp_path: Path):
    runner = FakeRunner(
        {
            "failed.jpg": RuntimeError("model could not read image"),
            "working.jpg": RAW_TEXT,
        }
    )
    adapter = LocalDamageModelAdapter(FakeStorage(tmp_path), runner)

    result = adapter.analyze(
        [evidence(1, "failed.jpg"), evidence(2, "working.jpg")]
    )

    assert len(result.records) == 1
    assert result.records[0].source_evidence_id == 2
    assert len(result.warnings) == 1
    assert "failed.jpg" in result.warnings[0]


def test_analysis_result_exposes_one_aggregate_record_for_multiple_images(tmp_path: Path):
    runner = FakeRunner({"first.jpg": RAW_TEXT, "second.jpg": RAW_TEXT})
    adapter = LocalDamageModelAdapter(FakeStorage(tmp_path), runner)

    result = adapter.analyze(
        [evidence(1, "first.jpg"), evidence(2, "second.jpg")]
    )

    output = result.to_dict()
    assert output["record"]["source_evidence_ids"] == [1, 2]
    assert output["record"]["annotated_evidence_ids"] == [1, 2]
    assert len(output["record"]["parts"]) == 2
    assert output["record"]["raw_text"] == f"{RAW_TEXT}\n\n{RAW_TEXT}"


def test_local_adapter_reports_unavailable_when_all_images_fail(tmp_path: Path):
    adapter = LocalDamageModelAdapter(
        FakeStorage(tmp_path),
        FakeRunner({"failed.jpg": RuntimeError("package unavailable")}),
    )

    with pytest.raises(DamageModelUnavailableError, match="all vehicle images"):
        adapter.analyze([evidence(1, "failed.jpg")])


def test_damage_model_factory_selects_mock_or_local_adapter(tmp_path: Path):
    mock_settings = SimpleNamespace(damage_model_mode="mock")
    local_settings = SimpleNamespace(damage_model_mode="local")
    storage = FakeStorage(tmp_path)

    assert isinstance(get_damage_model_adapter(mock_settings, storage), MockDamageModelAdapter)
    assert isinstance(get_damage_model_adapter(local_settings, storage), LocalDamageModelAdapter)
