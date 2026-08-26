"""Manufacturer-specific ampacity references for fire-rated cable families.

Manufacturer values stay separate from IEC 60364 table data. The narrow V0
slice only includes exact constructions needed by the anonymized reference
cases; values are never interpolated.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ManufacturerAmpacityRecord:
    family: str
    construction: str
    phase_conductor_mm2: float
    current_capacity_air_a: float
    ambient_c: float
    conductor_material: str
    ampacity_basis: str
    primary_source: str
    cross_check_source: str | None
    fire_performance_basis: tuple[str, ...]
    e90_note: str


NHXH_FE180_E90_AIR_30C = {
    "3x95+50": ManufacturerAmpacityRecord(
        family="NHXH FE180/E90", construction="3x95+50", phase_conductor_mm2=95.0,
        current_capacity_air_a=305.0, ambient_c=30.0, conductor_material="copper",
        ampacity_basis="manufacturer published current capacity in air; DIN VDE 0298-4 basis",
        primary_source="TT Cables (N)HXH (FRHF) FE180/E90 technical data family",
        cross_check_source="Halley Cables NHXH FE180/E90 technical table",
        fire_performance_basis=("IEC 60331", "IEC 60332", "IEC 60754", "IEC 61034"),
        e90_note="E90 is a system circuit-integrity classification and depends on the tested installation/support system.",
    ),
    "3x120+70": ManufacturerAmpacityRecord(
        family="NHXH FE180/E90", construction="3x120+70", phase_conductor_mm2=120.0,
        current_capacity_air_a=355.0, ambient_c=30.0, conductor_material="copper",
        ampacity_basis="manufacturer published current capacity in air; DIN VDE 0298-4 basis",
        primary_source="TT Cables (N)HXH (FRHF) FE180/E90 technical data family",
        cross_check_source="Halley/Qingzhou NHXH FE180/E90 technical tables",
        fire_performance_basis=("IEC 60331", "IEC 60332", "IEC 60754", "IEC 61034"),
        e90_note="E90 is a system circuit-integrity classification and depends on the tested installation/support system.",
    ),
    "5x25": ManufacturerAmpacityRecord(
        family="NHXH FE180/E90", construction="5x25", phase_conductor_mm2=25.0,
        current_capacity_air_a=130.0, ambient_c=30.0, conductor_material="copper",
        ampacity_basis="manufacturer published current capacity in air; DIN VDE 0298-4 basis",
        primary_source="NHXH FE180/E90 manufacturer technical table", cross_check_source=None,
        fire_performance_basis=("IEC 60331", "IEC 60332", "IEC 60754", "IEC 61034"),
        e90_note="E90 is a system circuit-integrity classification and depends on the tested installation/support system.",
    ),
    "5x10": ManufacturerAmpacityRecord(
        family="NHXH FE180/E90", construction="5x10", phase_conductor_mm2=10.0,
        current_capacity_air_a=73.0, ambient_c=30.0, conductor_material="copper",
        ampacity_basis="manufacturer published current capacity in air; DIN VDE 0298-4 basis",
        primary_source="NHXH FE180/E90 manufacturer technical table", cross_check_source=None,
        fire_performance_basis=("IEC 60331", "IEC 60332", "IEC 60754", "IEC 61034"),
        e90_note="E90 is a system circuit-integrity classification and depends on the tested installation/support system.",
    ),
}


def _normalize_construction(construction: str) -> str:
    return construction.lower().replace(" ", "").replace("mm2", "").replace("mm²", "")


def get_nhxh_fe180_e90_air_30c(construction: str) -> ManufacturerAmpacityRecord | None:
    """Return an exact-construction manufacturer record; never interpolate."""
    return NHXH_FE180_E90_AIR_30C.get(_normalize_construction(construction))


def get_nhxh_phase_conductor_mm2(construction: str) -> float | None:
    """Return the documented phase-conductor section for an exact construction."""
    record = get_nhxh_fe180_e90_air_30c(construction)
    return record.phase_conductor_mm2 if record else None
