"""Combined V0 feeder checker.

This orchestrates the design-current, breaker, cable-ampacity and voltage-drop
modules. Numerical failures are reported as FAIL. A numerical success is only
reported as PASS when all required engineering/standards layers used by the
combined verdict are verified; otherwise the feeder remains NOT VERIFIED.
"""
from dataclasses import dataclass
from typing import Literal

from .breaker import BreakerComparisonResult, compare_breaker
from .cable import AmpacityResult, CableAmpacityInput, calculate_supported_iz
from .current import CurrentResult, calculate_design_current
from .voltage_drop import VoltageDropResult, calculate_voltage_drop

OverallOutcome = Literal["PASS", "FAIL", "NOT VERIFIED"]


@dataclass(frozen=True)
class FeederInput:
    load_type: Literal["kw", "kva", "a"]
    load_value: float
    voltage_v: float | None
    phase: Literal["single", "three"] | None
    power_factor: float | None
    demand_factor: float = 1.0
    design_margin: float | None = None
    breaker_in_a: float | None = None
    cable: CableAmpacityInput | None = None
    length_m: float | None = None
    voltage_drop_cross_section_mm2: float | None = None
    voltage_drop_material: Literal["copper", "aluminium"] | None = None
    resistivity_ohm_mm2_per_m: float | None = None
    reactance_ohm_per_m: float | None = None
    impedance_source: str | None = None
    permitted_voltage_drop_percent: float | None = None
    voltage_drop_limit_source: str | None = None
    allow_annex_g_defaults: bool = False


@dataclass(frozen=True)
class AmpacityComparison:
    comparison: Literal["PASS", "FAIL", "NOT VERIFIED"]
    ib_a: float
    iz_a: float | None
    headroom_a: float | None


@dataclass(frozen=True)
class FeederResult:
    overall_outcome: OverallOutcome
    current: CurrentResult
    breaker: BreakerComparisonResult | None
    ampacity: AmpacityResult | None
    ampacity_comparison: AmpacityComparison
    voltage_drop: VoltageDropResult | None
    missing_or_unverified: tuple[str, ...]
    verification_summary: tuple[str, ...]


def _breaker_verified_for_overall(result: BreakerComparisonResult | None) -> bool:
    if result is None:
        return False
    status = result.standards_status.upper()
    return "NOT IEC VERIFIED" not in status and "NOT VERIFIED" not in status


def _ampacity_verified_for_overall(result: AmpacityResult | None) -> bool:
    if result is None or result.iz_a is None:
        return False
    status = result.status.upper()
    return "NOT VERIFIED" not in status


def check_feeder(data: FeederInput) -> FeederResult:
    current = calculate_design_current(
        load_type=data.load_type,
        load_value=data.load_value,
        voltage_v=data.voltage_v,
        phase=data.phase,
        power_factor=data.power_factor,
        demand_factor=data.demand_factor,
        design_margin=data.design_margin,
    )
    ib = current.design_current_a

    missing: list[str] = []
    verification: list[str] = [f"Current: {current.standards_status}"]

    breaker = None
    breaker_failed = False
    if data.breaker_in_a is None:
        missing.append("breaker_in_a")
    else:
        breaker = compare_breaker(ib_a=ib, in_a=data.breaker_in_a)
        breaker_failed = breaker.comparison == "FAIL"
        verification.append(f"Breaker: {breaker.standards_status}")
        if not _breaker_verified_for_overall(breaker):
            missing.append("breaker protection rule/current IEC basis")

    ampacity = None
    if data.cable is None:
        ampacity_comparison = AmpacityComparison("NOT VERIFIED", ib, None, None)
        missing.append("cable ampacity inputs")
    else:
        ampacity = calculate_supported_iz(data.cable)
        verification.append(f"Ampacity: {ampacity.status}")
        if ampacity.iz_a is None:
            ampacity_comparison = AmpacityComparison("NOT VERIFIED", ib, None, None)
            missing.extend(ampacity.missing_or_unsupported)
        else:
            headroom = ampacity.iz_a - ib
            ampacity_comparison = AmpacityComparison(
                "PASS" if ib <= ampacity.iz_a else "FAIL", ib, ampacity.iz_a, headroom
            )
            if not _ampacity_verified_for_overall(ampacity):
                missing.append("cable ampacity standards/data basis")

    voltage_drop = None
    vd_failed = False
    vd_unverified = False
    vd_required = data.length_m is not None
    if vd_required:
        if data.phase is None or data.voltage_v is None:
            missing.append("phase/voltage required for voltage drop")
            vd_unverified = True
        elif data.voltage_drop_cross_section_mm2 is None or data.voltage_drop_material is None:
            missing.append("voltage-drop cable cross-section/material")
            vd_unverified = True
        else:
            voltage_drop = calculate_voltage_drop(
                current_a=ib,
                length_m=data.length_m,
                cross_section_mm2=data.voltage_drop_cross_section_mm2,
                system_voltage_v=data.voltage_v,
                phase=data.phase,
                material=data.voltage_drop_material,
                power_factor=data.power_factor,
                resistivity_ohm_mm2_per_m=data.resistivity_ohm_mm2_per_m,
                reactance_ohm_per_m=data.reactance_ohm_per_m,
                impedance_source=data.impedance_source,
                permitted_limit_percent=data.permitted_voltage_drop_percent,
                limit_source=data.voltage_drop_limit_source,
                allow_annex_g_defaults=data.allow_annex_g_defaults,
            )
            verification.append(f"Voltage drop: {voltage_drop.standards_status}")
            if voltage_drop.comparison == "FAIL":
                vd_failed = True
            elif voltage_drop.comparison == "NO LIMIT CHECKED":
                vd_unverified = True
                missing.append("permitted voltage-drop limit/source")

    ampacity_failed = ampacity_comparison.comparison == "FAIL"
    any_failure = breaker_failed or ampacity_failed or vd_failed

    if any_failure:
        overall: OverallOutcome = "FAIL"
    else:
        unresolved = (
            breaker is None
            or not _breaker_verified_for_overall(breaker)
            or not _ampacity_verified_for_overall(ampacity)
            or ampacity_comparison.comparison == "NOT VERIFIED"
            or (vd_required and (voltage_drop is None or vd_unverified))
        )
        overall = "NOT VERIFIED" if unresolved else "PASS"

    return FeederResult(
        overall_outcome=overall,
        current=current,
        breaker=breaker,
        ampacity=ampacity,
        ampacity_comparison=ampacity_comparison,
        voltage_drop=voltage_drop,
        missing_or_unverified=tuple(dict.fromkeys(missing)),
        verification_summary=tuple(verification),
    )
