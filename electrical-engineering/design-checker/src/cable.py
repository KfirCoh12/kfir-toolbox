"""V0 cable ampacity model and first narrow Iz lookup.

The module supports one deliberately small IEC 60364-5-52:2009 data slice.
Unsupported conditions return NOT VERIFIED rather than being approximated.
"""
from dataclasses import dataclass
from typing import Literal

from .ampacity_data import (
    AMBIENT_AIR_FACTOR_XLPE_EPR,
    BASE_IZ_METHOD_E_3_LOADED,
    DATASET_METADATA,
)

Material = Literal["copper", "aluminium"]
Insulation = Literal["pvc", "xlpe_epr", "mineral", "other"]
Environment = Literal["air", "ground"]


@dataclass(frozen=True)
class CableAmpacityInput:
    material: Material
    cross_section_mm2: float
    insulation: Insulation
    loaded_conductors: int
    installation_method: str | None
    environment: Environment
    ambient_temperature_c: float | None = None
    ground_temperature_c: float | None = None
    soil_thermal_resistivity_km_per_w: float | None = None
    grouped_circuits: int | None = None
    parallel_runs: int = 1
    equal_current_sharing_confirmed: bool | None = None
    thdi_percent: float | None = None
    neutral_loaded: bool | None = None
    cable_data_source: str | None = None
    source_table_or_method: str | None = None


@dataclass(frozen=True)
class AmpacityResult:
    status: str
    iz_a: float | None
    base_iz_a: float | None
    correction_factors: tuple[tuple[str, float], ...]
    missing_or_unsupported: tuple[str, ...]
    trace: tuple[str, ...]
    source_metadata: dict


def calculate_supported_iz(data: CableAmpacityInput) -> AmpacityResult:
    if data.cross_section_mm2 <= 0:
        raise ValueError("cross_section_mm2 must be greater than 0")
    if data.loaded_conductors <= 0:
        raise ValueError("loaded_conductors must be greater than 0")
    if data.parallel_runs <= 0:
        raise ValueError("parallel_runs must be greater than 0")
    if data.grouped_circuits is not None and data.grouped_circuits <= 0:
        raise ValueError("grouped_circuits must be greater than 0 when supplied")
    if data.thdi_percent is not None and data.thdi_percent < 0:
        raise ValueError("thdi_percent cannot be negative")

    unsupported: list[str] = []
    trace: list[str] = []

    if data.insulation != "xlpe_epr":
        unsupported.append("V0 data slice supports XLPE/EPR only")
    if data.installation_method != "E":
        unsupported.append("V0 data slice supports IEC reference Method E only")
    if data.environment != "air":
        unsupported.append("V0 data slice supports air installations only")
    if data.loaded_conductors != 3:
        unsupported.append("V0 data slice supports three loaded conductors only")
    if data.grouped_circuits not in (None, 1):
        unsupported.append("grouping correction not implemented in this data slice")
    if data.parallel_runs != 1:
        unsupported.append("parallel-run aggregate Iz not implemented in this data slice")
    if data.thdi_percent is None:
        unsupported.append("thdi_percent is required to exclude unsupported harmonic treatment")
    elif data.thdi_percent > 15:
        unsupported.append("THDi > 15% requires harmonic/neutral treatment not implemented in this data slice")
    if data.neutral_loaded is None:
        unsupported.append("neutral_loaded must be stated explicitly")
    if data.ambient_temperature_c is None:
        unsupported.append("ambient_temperature_c is required")

    sizes = BASE_IZ_METHOD_E_3_LOADED.get(data.material, {})
    base = sizes.get(float(data.cross_section_mm2))
    if base is None:
        unsupported.append("cross-section/material combination is outside the narrow V0 dataset")

    factor = None
    if data.ambient_temperature_c is not None:
        factor = AMBIENT_AIR_FACTOR_XLPE_EPR.get(float(data.ambient_temperature_c))
        if factor is None:
            unsupported.append("ambient temperature is outside the narrow V0 correction-factor dataset")

    if unsupported:
        return AmpacityResult(
            status="NOT VERIFIED",
            iz_a=None,
            base_iz_a=base,
            correction_factors=tuple(),
            missing_or_unsupported=tuple(unsupported),
            trace=tuple(trace),
            source_metadata=DATASET_METADATA,
        )

    assert base is not None and factor is not None
    iz = base * factor
    trace.append(f"Base Iz = {base:.3f} A from {DATASET_METADATA['standard']} Table {DATASET_METADATA['base_ampacity_tables'][data.material]}")
    trace.append(f"Ambient-air factor = {factor:.3f} from Table {DATASET_METADATA['ambient_air_table']} at {data.ambient_temperature_c:.1f} °C")
    trace.append(f"Corrected Iz = {base:.3f} × {factor:.3f} = {iz:.3f} A")
    trace.append(DATASET_METADATA["current_edition_status"])

    return AmpacityResult(
        status="IEC 60364-5-52:2009 BASE-EDITION VERIFIED",
        iz_a=iz,
        base_iz_a=base,
        correction_factors=(("ambient_air", factor),),
        missing_or_unsupported=tuple(),
        trace=tuple(trace),
        source_metadata=DATASET_METADATA,
    )
