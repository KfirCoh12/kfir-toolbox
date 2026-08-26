"""Route cable ampacity lookups by evidence source.

Generic IEC table data and manufacturer-specific cable data remain separate.
Unsupported conditions return NOT VERIFIED rather than being approximated.
"""
from dataclasses import dataclass
from typing import Literal

from .cable import CableAmpacityInput, AmpacityResult, calculate_supported_iz
from .manufacturer_ampacity import get_nhxh_fe180_e90_air_30c

SourceKind = Literal["iec_generic", "manufacturer_nhxh_fe180_e90"]


@dataclass(frozen=True)
class RoutedAmpacityInput:
    source_kind: SourceKind
    generic: CableAmpacityInput | None = None
    construction: str | None = None
    ambient_temperature_c: float | None = None
    grouped_circuits: int = 1
    parallel_runs: int = 1
    equal_current_sharing_confirmed: bool | None = None


def calculate_routed_ampacity(data: RoutedAmpacityInput) -> AmpacityResult:
    if data.grouped_circuits <= 0:
        raise ValueError("grouped_circuits must be greater than 0")
    if data.parallel_runs <= 0:
        raise ValueError("parallel_runs must be greater than 0")

    if data.source_kind == "iec_generic":
        if data.generic is None:
            return AmpacityResult(
                status="NOT VERIFIED", iz_a=None, base_iz_a=None, correction_factors=tuple(),
                missing_or_unsupported=("generic IEC cable input is required",), trace=tuple(),
                source_metadata={"source_kind": "iec_generic"},
            )
        return calculate_supported_iz(data.generic)

    if data.source_kind == "manufacturer_nhxh_fe180_e90":
        missing: list[str] = []
        if not data.construction:
            missing.append("exact NHXH construction is required")
        if data.ambient_temperature_c != 30.0:
            missing.append("V0 manufacturer slice is verified only at 30 °C ambient")
        if data.grouped_circuits != 1:
            missing.append("manufacturer grouping correction source is not yet integrated")
        if data.parallel_runs > 1:
            if data.equal_current_sharing_confirmed is not True:
                missing.append("parallel runs require explicit acceptable current-sharing confirmation")
            missing.append("parallel/grouped manufacturer ampacity correction is not yet integrated")

        record = get_nhxh_fe180_e90_air_30c(data.construction or "")
        if record is None:
            missing.append("exact NHXH construction is outside the narrow manufacturer dataset")

        if missing:
            return AmpacityResult(
                status="NOT VERIFIED", iz_a=None,
                base_iz_a=record.current_capacity_air_a if record else None,
                correction_factors=tuple(), missing_or_unsupported=tuple(missing),
                trace=("Manufacturer source selected; V0 refuses to apply unsourced correction factors.",),
                source_metadata={"source_kind": "manufacturer", "family": "NHXH FE180/E90", "construction": data.construction},
            )

        assert record is not None
        return AmpacityResult(
            status="MANUFACTURER DATA VERIFIED — INSTALLATION CONDITIONS LIMITED",
            iz_a=record.current_capacity_air_a, base_iz_a=record.current_capacity_air_a,
            correction_factors=tuple(), missing_or_unsupported=tuple(),
            trace=(
                f"Manufacturer base Iz = {record.current_capacity_air_a:.1f} A for {record.construction} in air at 30 °C.",
                f"Phase conductor section = {record.phase_conductor_mm2:.1f} mm².",
                f"Ampacity basis: {record.ampacity_basis}.",
                f"Primary source: {record.primary_source}.", record.e90_note,
            ),
            source_metadata={
                "source_kind": "manufacturer", "family": record.family, "construction": record.construction,
                "phase_conductor_mm2": record.phase_conductor_mm2, "ambient_c": record.ambient_c,
                "ampacity_basis": record.ampacity_basis, "primary_source": record.primary_source,
                "cross_check_source": record.cross_check_source, "fire_performance_basis": record.fire_performance_basis,
            },
        )

    raise ValueError(f"unsupported source_kind: {data.source_kind}")
