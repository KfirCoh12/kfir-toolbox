"""Transparent V0 design-current calculations; no IEC compliance claim."""
from dataclasses import dataclass
from math import sqrt
from typing import Literal

from .validation import require_choice, require_positive_finite, require_unit_interval

Phase = Literal["single", "three"]
LoadType = Literal["kw", "kva", "a"]


@dataclass(frozen=True)
class CurrentResult:
    design_current_a: float
    base_current_a: float
    demand_factor: float
    design_margin: float | None
    margin_adjusted_current_a: float | None
    formula: str
    calculation_trace: tuple[str, ...]
    standards_status: str = "CALCULATED — NOT IEC VERIFIED"


def calculate_design_current(
    *,
    load_type: LoadType,
    load_value: float,
    voltage_v: float | None = None,
    phase: Phase | None = None,
    power_factor: float | None = None,
    demand_factor: float = 1.0,
    design_margin: float | None = None,
) -> CurrentResult:
    require_positive_finite("load_value", load_value)
    require_unit_interval("demand_factor", demand_factor)
    if design_margin is not None:
        require_unit_interval("design_margin", design_margin)

    trace = []
    if load_type == "a":
        base = load_value
        formula = "I = supplied current"
        trace.append(f"Base current = {base:.6f} A (supplied directly)")
    elif load_type in {"kw", "kva"}:
        if voltage_v is None or phase is None:
            raise ValueError("voltage_v and phase are required for kW/kVA loads")
        require_positive_finite("voltage_v", voltage_v)
        require_choice("phase", phase, ("single", "three"))
        phase_factor = sqrt(3) if phase == "three" else 1.0

        if load_type == "kw":
            if power_factor is None:
                raise ValueError("power_factor is required for kW loads")
            require_unit_interval("power_factor", power_factor)
            base = load_value * 1000 / (phase_factor * voltage_v * power_factor)
            formula = (
                "I = P / (sqrt(3) × V × PF)"
                if phase == "three"
                else "I = P / (V × PF)"
            )
        else:
            base = load_value * 1000 / (phase_factor * voltage_v)
            formula = (
                "I = S / (sqrt(3) × V)" if phase == "three" else "I = S / V"
            )
        trace.append(f"Base current = {base:.6f} A")
    else:
        raise ValueError("load_type must be 'kw', 'kva', or 'a'")

    ib = base * demand_factor
    trace.append(f"Ib = {base:.6f} × {demand_factor:.6g} = {ib:.6f} A")
    adjusted = None
    if design_margin is not None:
        adjusted = ib / design_margin
        trace.append(
            f"Project margin current = {ib:.6f} / {design_margin:.6g} = {adjusted:.6f} A"
        )
        trace.append("Project margin is not treated as an IEC requirement.")

    return CurrentResult(
        ib,
        base,
        demand_factor,
        design_margin,
        adjusted,
        formula,
        tuple(trace),
    )
