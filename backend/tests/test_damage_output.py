from app.models import DamageDetectionStatus
from app.services.damage_output import (
    normalize_damage_text,
    parse_damage_text,
)


RAW_DAMAGE_TEXT = """
Windshield | Total Damage: 94.51% | Part Conf: 0.88
   ├─ glass shatter   | Area:  94.51% | Pixels: 14,642 | Conf: 0.57

Roof | Total Damage: 12.64% | Part Conf: 0.54
   ├─ glass shatter   | Area:  12.64% | Pixels: 332 | Conf: 0.57

Front-bumper | Total Damage: 7.75% | Part Conf: 0.86
   ├─ scratch         | Area:   7.01% | Pixels: 1,741 | Conf: 0.29
   └─ lamp broken     | Area:   0.74% | Pixels: 183 | Conf: 0.62
"""


def test_parse_damage_text_preserves_parts_and_nested_details():
    parts = parse_damage_text(RAW_DAMAGE_TEXT)

    assert [part.vehicle_part for part in parts] == ["Windshield", "Roof", "Front-bumper"]
    assert parts[0].total_damage_percentage == 94.51
    assert parts[0].part_confidence == 0.88
    assert parts[0].damage_details[0].damage_type == "glass shatter"
    assert parts[0].damage_details[0].pixels == 14642
    assert [detail.damage_type for detail in parts[2].damage_details] == [
        "scratch",
        "lamp broken",
    ]


def test_normalize_damage_text_keeps_raw_text_and_maps_parts_to_existing_detections():
    record = normalize_damage_text(
        RAW_DAMAGE_TEXT,
        source_evidence_id=7,
        annotated_evidence_id=7,
    )

    assert record.raw_text == RAW_DAMAGE_TEXT
    assert record.part_identities == ("Windshield", "Roof", "Front-bumper")
    assert len(record.parts) == 3

    detections = record.to_detections()
    assert len(detections) == 3
    assert detections[0].source_evidence_id == 7
    assert detections[0].vehicle_part == "Windshield"
    assert detections[0].damage_percentage == 94.51
    assert detections[0].confidence == 0.88
    assert detections[2].damage_type == "scratch, lamp broken"
    assert detections[2].status is DamageDetectionStatus.DETECTED


def test_parse_damage_text_ignores_malformed_lines_without_losing_valid_parts():
    parts = parse_damage_text(
        """
        not a damage record
        Door | Total Damage: bad | Part Conf: 0.80
        Door | Total Damage: 20.00% | Part Conf: 0.80
        malformed | Area: 10% | Pixels: nope | Conf: 0.4
        """
    )

    assert len(parts) == 1
    assert parts[0].vehicle_part == "Door"
    assert parts[0].damage_details == ()


def test_parse_damage_text_returns_empty_output_for_empty_or_whitespace_input():
    assert parse_damage_text("") == ()
    assert parse_damage_text("  \n\t") == ()
