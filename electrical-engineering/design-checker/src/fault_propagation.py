"""Conservative downstream 3-phase fault-current screening through a cable.

The model converts an upstream prospective 3-phase RMS fault current into an
upstream Thevenin-impedance magnitude and adds only a minimum series conductor
resistance for the cable. Cable reactance is deliberately omitted and the conductor
resistance uses fixed 20 °C reference resistivity values, both of which keep the
calculated downstream current on the high side for the stated passive-network
assumptions.

This is a breaking-capacity screening aid, not an IEC 60909 short-circuit study and
not manufacturer cable data.
"""
from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Literal

ConductorMaterial = Literal["copper", "aluminium"]

# Nominal 20 °C resistivity values used only for the narrow screening model.
# They are explicit calculation constants, not a manufacturer cable dataset.
_RESISTIVITY_OHM_MM2_PER_M: dict[ConductorMaterial, float] = {
    "copper": 0.017241,
    "aluminium": 0.028264,
}


@dataclass(frozen=True)
class CableFaultPath:
    circuit_id: str
    material: ConductorMaterial
    cross_section_mm2: float
    parallel_runs: int
    length_m: float


@dataclass(frozen=True)
class DownstreamFaultEstimate:
    upstream_fault_current_ka: float
    prospective_fault_current_ka: float
    source_impedance_magnitude_ohm: float
    cable_resistance_ohm: float
    minimum_total_impedance_magnitude_ohm: float
    path: CableFaultPath
    basis: str


def _positive(name: str, value: float) -> float:
    number = float(value)
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be a finite value greater than 0")
    return number


def cable_conductor_resistance_ohm(path: CableFaultPath) -> float:
    """Return one-phase conductor resistance for the declared cable path."""
    if path.material not in _RESISTIVITY_OHM_MM2_PER_M:
        raise ValueError("unsupported conductor material")
    area = _positive("cross_section_mm2", path.cross_section_mm2)
    length = _positive("length_m", path.length_m)
    runs = int(path.parallel_runs)
    if runs <= 0:
        raise ValueError("parallel_runs must be greater than 0")
    return _RESISTIVITY_OHM_MM2_PER_M[path.material] * length / (area * runs)


def propagate_three_phase_fault_screening(
    *,
    upstream_fault_current_ka: float,
    line_to_line_voltage_v: float,
    path: CableFaultPath,
) -> DownstreamFaultEstimate:
    """Return a conservative high-side downstream 3-phase fault-current estimate.

    The upstream fault current defines only the magnitude of the upstream Thevenin
    impedance. With a passive source (non-negative R and X), adding a positive cable
    resistance gives |Z_total| >= sqrt(|Z_source|^2 + R_cable^2). Using that lower
    bound on total impedance therefore gives an upper screening estimate of current.

    Cable reactance, elevated conductor temperature, joints and other series
    impedances are omitted; those omissions further prevent this helper from claiming
    a full short-circuit study.
    """
    fault_ka = _positive("upstream_fault_current_ka", upstream_fault_current_ka)
    voltage = _positive("line_to_line_voltage_v", line_to_line_voltage_v)
    resistance = cable_conductor_resistance_ohm(path)

    source_z = voltage / (sqrt(3.0) * fault_ka * 1000.0)
    minimum_total_z = sqrt(source_z * source_z + resistance * resistance)
    downstream_ka = voltage / (sqrt(3.0) * minimum_total_z) / 1000.0

    return DownstreamFaultEstimate(
        upstream_fault_current_ka=fault_ka,
        prospective_fault_current_ka=downstream_ka,
        source_impedance_magnitude_ohm=source_z,
        cable_resistance_ohm=resistance,
        minimum_total_impedance_magnitude_ohm=minimum_total_z,
        path=path,
        basis=(
            f"3-phase breaking-capacity screening via {path.circuit_id}: upstream "
            f"{fault_ka:.3f} kA at {voltage:g} V, {path.length_m:g} m of "
            f"{path.parallel_runs} × {path.cross_section_mm2:g} mm² {path.material} "
            f"gives R20={resistance:.6f} ohm and downstream screening current "
            f"{downstream_ka:.3f} kA. Cable reactance, hot resistance, joints and "
            "additional network impedance are omitted. This is not IEC 60909."
        ),
    )
