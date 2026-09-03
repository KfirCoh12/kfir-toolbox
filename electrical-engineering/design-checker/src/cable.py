"""V0 cable ampacity model and narrow IEC 60364-5-52:2009 Iz lookup.

Unsupported conditions return NOT VERIFIED rather than being approximated.
"""
from dataclasses import dataclass
from typing import Literal

from .ampacity_data import (
    AMBIENT_AIR_FACTOR_XLPE_EPR,
    BASE_IZ_METHOD_E_BY_LOADED_CONDUCTORS,
    DATASET_METADATA,
    GROUPING_FACTOR_B5217,
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
    grouping_arrangement: str | None = None
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
    if data.loaded_conductors not in BASE_IZ_METHOD_E_BY_LOADED_CONDUCTORS:
        unsupported.append("V0 data slice supports two or three loaded conductors only")
    if data.thdi_percent is None:
        unsupported.append("thdi_percent is required to exclude unsupported harmonic treatment")
    elif data.thdi_percent > 15:
        unsupported.append("THDi > 15% requires harmonic/neutral treatment not implemented in this data slice")
    if data.neutral_loaded is None:
        unsupported.append("neutral_loaded must be stated explicitly")
    if data.ambient_temperature_c is None:
        unsupported.append("ambient_temperature_c is required")

    loaded_dataset = BASE_IZ_METHOD_E_BY_LOADED_CONDUCTORS.get(data.loaded_conductors, {})
    sizes = loaded_dataset.get(data.material, {})
    base = sizes.get(float(data.cross_section_mm2))
    if base is None:
        unsupported.append("cross-section/material/loaded-conductor combination is outside the narrow V0 dataset")

    ambient_factor = None
    if data.ambient_temperature_c is not None:
        ambient_factor = AMBIENT_AIR_FACTOR_XLPE_EPR.get(float(data.ambient_temperature_c))
        if ambient_factor is None:
            unsupported.append("ambient temperature is outside the narrow V0 correction-factor dataset")

    grouping_factor = None
    if data.grouped_circuits is None:
        unsupported.append("grouped_circuits must be stated explicitly")
    elif data.grouped_circuits == 1:
        grouping_factor = 1.0
    else:
        if not data.grouping_arrangement:
            unsupported.append("grouping_arrangement is required when more than one circuit/cable is grouped")
        else:
            arrangement = GROUPING_FACTOR_B5217.get(data.grouping_arrangement)
            if arrangement is None:
                unsupported.append("grouping arrangement is outside the selected B.52.17 V0 subset")
            else:
                grouping_factor = arrangement.get(data.grouped_circuits)
                if grouping_factor is None:
                    unsupported.append("group count is outside the selected B.52.17 V0 subset")

    if data.parallel_runs > 1:
        if data.equal_current_sharing_confirmed is not True:
            unsupported.append("parallel runs require explicit confirmation of acceptable current sharing per 523.7")
        if data.grouped_circuits is None or data.grouped_circuits < data.parallel_runs:
            unsupported.append("parallel runs require grouping input that includes at least all parallel cable runs")

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

    assert base is not None and ambient_factor is not None and grouping_factor is not None
    per_run_iz = base * ambient_factor * grouping_factor
    aggregate_iz = per_run_iz * data.parallel_runs
    loaded_label = DATASET_METADATA["base_ampacity_columns"][data.loaded_conductors]

    trace.append(
        f"Base Iz per run = {base:.3f} A from {DATASET_METADATA['standard']} "
        f"Table {DATASET_METADATA['base_ampacity_tables'][data.material]} ({loaded_label})"
    )
    trace.append(f"Ambient-air factor = {ambient_factor:.3f} from Table {DATASET_METADATA['ambient_air_table']} at {data.ambient_temperature_c:.1f} °C")
    trace.append(f"Grouping factor = {grouping_factor:.3f} from Table {DATASET_METADATA['grouping_table']} for {data.grouped_circuits} relevant circuit(s)/cable(s)")
    trace.append(f"Corrected Iz per run = {base:.3f} × {ambient_factor:.3f} × {grouping_factor:.3f} = {per_run_iz:.3f} A")
    if data.parallel_runs > 1:
        trace.append(f"Aggregate Iz = {per_run_iz:.3f} × {data.parallel_runs} parallel runs = {aggregate_iz:.3f} A; current-sharing condition explicitly confirmed")
    trace.append(DATASET_METADATA["current_edition_status"])

    return AmpacityResult(
        status="IEC 60364-5-52:2009 BASE-EDITION VERIFIED",
        iz_a=aggregate_iz,
        base_iz_a=base,
        correction_factors=(("ambient_air", ambient_factor), ("grouping", grouping_factor)),
        missing_or_unsupported=tuple(),
        trace=tuple(trace),
        source_metadata=DATASET_METADATA,
    )
