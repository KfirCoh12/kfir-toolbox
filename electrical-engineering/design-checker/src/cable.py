"""V0 cable ampacity input model and readiness validation.

No ampacity tables are encoded here. This module only represents the engineering
conditions needed before an Iz lookup/calculation can be attempted.

Source basis for the input structure:
- IEC 60364-5-52:2009 Ed. 3.0, Clause 523
- Installation-method mapping in Annex A
- Ampacity/correction-factor structure in Annex B
- Parallel-conductor considerations in 523.7
- Harmonic/loading considerations in 523.6 and Annex E

Until the required data source and exact applicable table/rule are resolved, the
module returns NOT VERIFIED rather than inventing Iz.
"""
from dataclasses import dataclass
from typing import Literal

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
class AmpacityReadinessResult:
    ready_for_iz_lookup: bool
    missing_or_unverified: tuple[str, ...]
    notes: tuple[str, ...]
    standards_status: str = "NOT VERIFIED"


def validate_ampacity_inputs(data: CableAmpacityInput) -> AmpacityReadinessResult:
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

    missing: list[str] = []
    notes: list[str] = []

    if not data.installation_method:
        missing.append("installation_method")
    if not data.cable_data_source:
        missing.append("cable_data_source")
    if not data.source_table_or_method:
        missing.append("source_table_or_method")

    if data.environment == "air":
        if data.ambient_temperature_c is None:
            missing.append("ambient_temperature_c")
    elif data.environment == "ground":
        if data.ground_temperature_c is None:
            missing.append("ground_temperature_c")
        if data.soil_thermal_resistivity_km_per_w is None:
            missing.append("soil_thermal_resistivity_km_per_w")

    if data.grouped_circuits is None:
        missing.append("grouped_circuits")

    if data.parallel_runs > 1 and data.equal_current_sharing_confirmed is not True:
        missing.append("equal_current_sharing_confirmed")
        notes.append("Parallel runs require current-sharing conditions to be verified before aggregate Iz is used.")

    if data.neutral_loaded is None:
        missing.append("neutral_loaded")

    if data.thdi_percent is None:
        missing.append("thdi_percent")
    elif data.thdi_percent > 15:
        notes.append("THDi exceeds 15%; neutral/harmonic effects require explicit treatment before Iz is accepted.")

    if data.insulation == "other":
        notes.append("Insulation type is outside the built-in V0 categories; manufacturer/product data is required.")

    ready = len(missing) == 0
    status = "CALCULATED INPUTS READY — IZ NOT YET IMPLEMENTED" if ready else "NOT VERIFIED"
    return AmpacityReadinessResult(ready, tuple(missing), tuple(notes), status)
