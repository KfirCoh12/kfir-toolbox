"""Voltage-drop calculation based on IEC 60364-5-52:2009 Annex G.

Annex G is informative. This module therefore separates the numerical
calculation from any permitted-limit verdict and never presents Annex G
guidance as a universal mandatory compliance rule.
"""
from dataclasses import dataclass
from math import sqrt
from typing import Literal

Phase = Literal["single", "three"]
Material = Literal["copper", "aluminium"]
SupplyType = Literal["public_lv", "private_lv"]
UseType = Literal["lighting", "other"]

# Annex G fallback values at normal service conditions.
ANNEX_G_RESISTIVITY_OHM_MM2_PER_M = {
    "copper": 0.0225,
    "aluminium": 0.0360,
}
ANNEX_G_REACTANCE_OHM_PER_M = 0.00008

# Informative guidance from Table G.52.1, not a universal mandatory rule.
ANNEX_G_GUIDANCE_LIMIT_PERCENT = {
    ("public_lv", "lighting"): 3.0,
    ("public_lv", "other"): 5.0,
    ("private_lv", "lighting"): 6.0,
    ("private_lv", "other"): 8.0,
}


@dataclass(frozen=True)
class VoltageDropResult:
    voltage_drop_v: float
    voltage_drop_percent: float
    line_to_neutral_voltage_v: float
    power_factor: float
    resistivity_ohm_mm2_per_m: float
    reactance_ohm_per_m: float
    permitted_limit_percent: float | None
    limit_source: str | None
    comparison: str
    trace: tuple[str, ...]
    standards_status: str


def annex_g_guidance_limit_percent(
    *,
    supply_type: SupplyType,
    use_type: UseType,
    main_wiring_length_m: float | None = None,
) -> float:
    """Return Annex G informative guidance, including its long-run allowance."""
    base = ANNEX_G_GUIDANCE_LIMIT_PERCENT[(supply_type, use_type)]
    if main_wiring_length_m is None or main_wiring_length_m <= 100:
        return base
    extra = min((main_wiring_length_m - 100.0) * 0.005, 0.5)
    return base + extra


def calculate_voltage_drop(
    *,
    current_a: float,
    length_m: float,
    cross_section_mm2: float,
    system_voltage_v: float,
    phase: Phase,
    material: Material,
    power_factor: float | None,
    resistivity_ohm_mm2_per_m: float | None = None,
    reactance_ohm_per_m: float | None = None,
    impedance_source: str | None = None,
    permitted_limit_percent: float | None = None,
    limit_source: str | None = None,
    allow_annex_g_defaults: bool = False,
) -> VoltageDropResult:
    """Calculate voltage drop using the Annex G expression.

    ``system_voltage_v`` is line-line voltage for a three-phase circuit and
    line-neutral voltage for a single-phase circuit. For percentage voltage
    drop, the Annex G denominator U0 is line-neutral voltage.

    Annex G fallback PF/resistivity/reactance values are used only when
    ``allow_annex_g_defaults`` is True, so assumptions are never silent.
    """
    for name, value in (
        ("current_a", current_a),
        ("length_m", length_m),
        ("cross_section_mm2", cross_section_mm2),
        ("system_voltage_v", system_voltage_v),
    ):
        if value <= 0:
            raise ValueError(f"{name} must be greater than 0")

    trace: list[str] = []

    if power_factor is None:
        if not allow_annex_g_defaults:
            raise ValueError("power_factor is required unless Annex G defaults are explicitly allowed")
        power_factor = 0.8
        trace.append("Power factor defaulted to 0.8 using IEC 60364-5-52:2009 Annex G guidance.")
    if not 0 < power_factor <= 1:
        raise ValueError("power_factor must be greater than 0 and at most 1")

    if resistivity_ohm_mm2_per_m is None:
        if not allow_annex_g_defaults:
            raise ValueError("resistivity is required unless Annex G defaults are explicitly allowed")
        resistivity_ohm_mm2_per_m = ANNEX_G_RESISTIVITY_OHM_MM2_PER_M[material]
        trace.append(
            f"Resistivity defaulted to {resistivity_ohm_mm2_per_m:.6g} ohm·mm²/m "
            f"for {material} using Annex G normal-service guidance."
        )
    elif resistivity_ohm_mm2_per_m <= 0:
        raise ValueError("resistivity_ohm_mm2_per_m must be greater than 0")

    if reactance_ohm_per_m is None:
        if not allow_annex_g_defaults:
            raise ValueError("reactance is required unless Annex G defaults are explicitly allowed")
        reactance_ohm_per_m = ANNEX_G_REACTANCE_OHM_PER_M
        trace.append(
            f"Reactance defaulted to {reactance_ohm_per_m:.6g} ohm/m using Annex G guidance."
        )
    elif reactance_ohm_per_m < 0:
        raise ValueError("reactance_ohm_per_m cannot be negative")

    if impedance_source:
        trace.append(f"User-supplied impedance source: {impedance_source}")

    b = 1.0 if phase == "three" else 2.0
    u0 = system_voltage_v / sqrt(3) if phase == "three" else system_voltage_v
    sin_phi = sqrt(max(0.0, 1.0 - power_factor**2))

    resistive_term = resistivity_ohm_mm2_per_m * length_m / cross_section_mm2 * power_factor
    reactive_term = reactance_ohm_per_m * length_m * sin_phi
    voltage_drop_v = b * (resistive_term + reactive_term) * current_a
    voltage_drop_percent = 100.0 * voltage_drop_v / u0

    trace.extend((
        f"Phase coefficient b = {b:.0f}",
        f"U0 = {u0:.6f} V (line-to-neutral basis)",
        f"sin(phi) = {sin_phi:.6f}",
        f"Resistive term = rho × L / S × cos(phi) = {resistive_term:.9f} ohm",
        f"Reactive term = X × L × sin(phi) = {reactive_term:.9f} ohm",
        f"Voltage drop u = {voltage_drop_v:.6f} V",
        f"Voltage drop = 100 × u / U0 = {voltage_drop_percent:.6f}%",
    ))

    if permitted_limit_percent is None:
        comparison = "NO LIMIT CHECKED"
        standards_status = "CALCULATED — IEC ANNEX G METHOD; LIMIT NOT VERIFIED"
    else:
        if permitted_limit_percent <= 0:
            raise ValueError("permitted_limit_percent must be greater than 0")
        if not limit_source:
            raise ValueError("limit_source is required when a permitted limit is supplied")
        comparison = "PASS" if voltage_drop_percent <= permitted_limit_percent else "FAIL"
        standards_status = "CALCULATED — LIMIT SOURCE EXPLICIT; IEC ANNEX G IS INFORMATIVE"
        trace.append(
            f"Limit comparison: {voltage_drop_percent:.6f}% <= {permitted_limit_percent:.6f}%: "
            f"{comparison} ({limit_source})"
        )

    return VoltageDropResult(
        voltage_drop_v=voltage_drop_v,
        voltage_drop_percent=voltage_drop_percent,
        line_to_neutral_voltage_v=u0,
        power_factor=power_factor,
        resistivity_ohm_mm2_per_m=resistivity_ohm_mm2_per_m,
        reactance_ohm_per_m=reactance_ohm_per_m,
        permitted_limit_percent=permitted_limit_percent,
        limit_source=limit_source,
        comparison=comparison,
        trace=tuple(trace),
        standards_status=standards_status,
    )
