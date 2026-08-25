"""Manufacturer-specific ampacity references for fire-rated cable families.

This module is deliberately separate from IEC 60364 ampacity tables. A value
published by a cable manufacturer is manufacturer data, even where the cable
construction/fire performance is tested to IEC standards and the ampacity is
stated against another recognised installation standard.

V0 first reference family:
- (N)HXH / NHXH FE180 E90, copper, 0.6/1 kV
- current capacity in air at 30 °C
- manufacturer/reference values are never relabelled as IEC 60364 table data

The small dataset below only covers constructions needed by the anonymized V0
reference cases. It is not a reproduction of a full catalogue.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ManufacturerAmpacityRecord:
    family: str
    construction: str
    current_capacity_air_a: float
    ambient_c: float
    conductor_material: str
    ampacity_basis: str
    primary_source: str
    cross_check_source: str | None
    fire_performance_basis: tuple[str, ...]
    e90_note: str


# Narrow reference slice needed by V0 real-world cases.
# Values are kept construction-specific so the checker never assumes that
# 95 mm² alone is enough to identify a manufacturer's current rating.
NHXH_FE180_E90_AIR_30C = {
    "3x95+50": ManufacturerAmpacityRecord(
        family="NHXH FE180/E90",
        construction="3x95+50",
        current_capacity_air_a=305.0,
        ambient_c=30.0,
        conductor_material="copper",
        ampacity_basis="manufacturer published current capacity in air; DIN VDE 0298-4 basis",
        primary_source="TT Cables (N)HXH (FRHF) FE180/E90 technical data family",
        cross_check_source="Halley Cables NHXH FE180/E90 technical table",
        fire_performance_basis=("IEC 60331", "IEC 60332", "IEC 60754", "IEC 61034"),
        e90_note="E90 is a system circuit-integrity classification and depends on the tested installation/support system.",
    ),
    "3x120+70": ManufacturerAmpacityRecord(
        family="NHXH FE180/E90",
        construction="3x120+70",
        current_capacity_air_a=355.0,
        ambient_c=30.0,
        conductor_material="copper",
        ampacity_basis="manufacturer published current capacity in air; DIN VDE 0298-4 basis",
        primary_source="TT Cables (N)HXH (FRHF) FE180/E90 technical data family",
        cross_check_source="Halley/Qingzhou NHXH FE180/E90 technical tables",
        fire_performance_basis=("IEC 60331", "IEC 60332", "IEC 60754", "IEC 61034"),
        e90_note="E90 is a system circuit-integrity classification and depends on the tested installation/support system.",
    ),
    "5x25": ManufacturerAmpacityRecord(
        family="NHXH FE180/E90",
        construction="5x25",
        current_capacity_air_a=130.0,
        ambient_c=30.0,
        conductor_material="copper",
        ampacity_basis="manufacturer published current capacity in air; DIN VDE 0298-4 basis",
        primary_source="NHXH FE180/E90 manufacturer technical table",
        cross_check_source=None,
        fire_performance_basis=("IEC 60331", "IEC 60332", "IEC 60754", "IEC 61034"),
        e90_note="E90 is a system circuit-integrity classification and depends on the tested installation/support system.",
    ),
    "5x10": ManufacturerAmpacityRecord(
        family="NHXH FE180/E90",
        construction="5x10",
        current_capacity_air_a=73.0,
        ambient_c=30.0,
        conductor_material="copper",
        ampacity_basis="manufacturer published current capacity in air; DIN VDE 0298-4 basis",
        primary_source="NHXH FE180/E90 manufacturer technical table",
        cross_check_source=None,
        fire_performance_basis=("IEC 60331", "IEC 60332", "IEC 60754", "IEC 61034"),
        e90_note="E90 is a system circuit-integrity classification and depends on the tested installation/support system.",
    ),
}


def get_nhxh_fe180_e90_air_30c(construction: str) -> ManufacturerAmpacityRecord | None:
    """Return an exact-construction manufacturer record; never interpolate."""
    key = construction.lower().replace(" ", "").replace("mm2", "").replace("mm²", "")
    return NHXH_FE180_E90_AIR_30C.get(key)
