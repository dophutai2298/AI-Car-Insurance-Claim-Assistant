from __future__ import annotations

from dataclasses import dataclass
import re

from app.models import DamageDetectionStatus
from app.services.damage_model import DamageModelDetection


PART_PATTERN = re.compile(
    r"^(?P<part>[^|]+?)\s*\|\s*"
    r"Total Damage:\s*(?P<total_damage>[\d.]+)%\s*\|\s*"
    r"Part Conf:\s*(?P<part_conf>[\d.]+)\s*$",
    re.IGNORECASE,
)

DAMAGE_PATTERN = re.compile(
    r"^(?P<damage_type>[^|]+?)\s*\|\s*"
    r"Area:\s*(?P<area>[\d.]+)%\s*\|\s*"
    r"Pixels:\s*(?P<pixels>[\d,]+)\s*\|\s*"
    r"Conf:\s*(?P<confidence>[\d.]+)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DamageDetail:
    damage_type: str
    area_percentage: float
    pixels: int
    confidence: float


@dataclass(frozen=True)
class DamagePart:
    vehicle_part: str
    total_damage_percentage: float
    part_confidence: float
    damage_details: tuple[DamageDetail, ...] = ()


@dataclass(frozen=True)
class CarDamageRecord:
    """The source-linked aggregate result for one model response."""

    source_evidence_id: int
    annotated_evidence_id: int
    raw_text: str
    parts: tuple[DamagePart, ...]

    @property
    def part_identities(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(part.vehicle_part for part in self.parts))

    def to_detections(self) -> list[DamageModelDetection]:
        """Adapt part-level output to the existing assessment/price-search contract."""
        return [
            DamageModelDetection(
                source_evidence_id=self.source_evidence_id,
                annotated_evidence_id=self.annotated_evidence_id,
                vehicle_part=part.vehicle_part,
                damage_type=_combined_damage_type(part.damage_details),
                damage_percentage=part.total_damage_percentage,
                confidence=part.part_confidence,
                status=DamageDetectionStatus.DETECTED,
            )
            for part in self.parts
        ]


def _strip_tree_prefix(line: str) -> str:
    # The model may use ASCII, Unicode, or mojibake tree characters as a prefix.
    return re.sub(r"^[^\w]+", "", line, flags=re.UNICODE).strip()


def _combined_damage_type(details: tuple[DamageDetail, ...]) -> str | None:
    types = list(dict.fromkeys(detail.damage_type for detail in details if detail.damage_type))
    return ", ".join(types) or None


def parse_damage_text(text: str) -> tuple[DamagePart, ...]:
    """Parse the reference raw-text format without side effects or model calls."""
    parts: list[DamagePart] = []
    current_part: DamagePart | None = None
    current_details: list[DamageDetail] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        part_match = PART_PATTERN.match(line)
        if part_match:
            if current_part is not None:
                parts.append(
                    DamagePart(
                        vehicle_part=current_part.vehicle_part,
                        total_damage_percentage=current_part.total_damage_percentage,
                        part_confidence=current_part.part_confidence,
                        damage_details=tuple(current_details),
                    )
                )
            current_part = DamagePart(
                vehicle_part=part_match.group("part").strip(),
                total_damage_percentage=float(part_match.group("total_damage")),
                part_confidence=float(part_match.group("part_conf")),
            )
            current_details = []
            continue

        detail_match = DAMAGE_PATTERN.match(_strip_tree_prefix(line))
        if detail_match and current_part is not None:
            current_details.append(
                DamageDetail(
                    damage_type=detail_match.group("damage_type").strip(),
                    area_percentage=float(detail_match.group("area")),
                    pixels=int(detail_match.group("pixels").replace(",", "")),
                    confidence=float(detail_match.group("confidence")),
                )
            )

    if current_part is not None:
        parts.append(
            DamagePart(
                vehicle_part=current_part.vehicle_part,
                total_damage_percentage=current_part.total_damage_percentage,
                part_confidence=current_part.part_confidence,
                damage_details=tuple(current_details),
            )
        )

    return tuple(parts)


def normalize_damage_text(
    raw_text: str,
    *,
    source_evidence_id: int,
    annotated_evidence_id: int,
) -> CarDamageRecord:
    return CarDamageRecord(
        source_evidence_id=source_evidence_id,
        annotated_evidence_id=annotated_evidence_id,
        raw_text=raw_text,
        parts=parse_damage_text(raw_text),
    )
