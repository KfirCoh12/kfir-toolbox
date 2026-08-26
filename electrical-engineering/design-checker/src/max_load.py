"""Reverse V0.6 solver: existing circuit -> maximum supported load."""
from dataclasses import dataclass
from math import sqrt
from typing import Literal

from .ampacity_router import RoutedAmpacityInput, calculate_routed_ampacity
from .connection import get_connection_option
from .voltage_drop import calculate_voltage_drop

Phase = Literal["single", "three"]

@dataclass(frozen=True)
class MaxLoadInput:
    voltage_v: float
    phase: Phase
    power_factor: float
    breaker_in_a: float | None = None
    connection_rating_a: float | None = None
    connection_option_id: str | None = None
    ampacity_route: RoutedAmpacityInput | None = None
    length_m: float | None = None
    voltage_drop_cross_section_mm2: float | None = None
    voltage_drop_material: Literal["copper", "aluminium"] | None = None
    permitted_voltage_drop_percent: float | None = None
    voltage_drop_limit_source: str | None = None
    allow_annex_g_defaults: bool = False

@dataclass(frozen=True)
class ConstraintLimit:
    name: str
    current_a: float
    detail: str

@dataclass(frozen=True)
class MaxLoadResult:
    status: Literal["RESULT", "NOT VERIFIED"]
    max_current_a: float | None
    max_kw: float | None
    max_kva: float | None
    limiting_constraint: str | None
    constraints: tuple[ConstraintLimit, ...]
    limitations: tuple[str, ...]
    trace: tuple[str, ...]

def _positive(name, value):
    if value <= 0: raise ValueError(f"{name} must be greater than 0")
def _kw_from_current(i,v,phase,pf): return (sqrt(3) if phase=="three" else 1.0)*v*i*pf/1000.0
def _kva_from_current(i,v,phase): return (sqrt(3) if phase=="three" else 1.0)*v*i/1000.0

def calculate_max_load(data: MaxLoadInput) -> MaxLoadResult:
    _positive("voltage_v",data.voltage_v)
    if not 0 < data.power_factor <= 1: raise ValueError("power_factor must be greater than 0 and at most 1")
    if data.connection_rating_a is not None and data.connection_option_id is not None: raise ValueError("Supply either connection_rating_a or connection_option_id, not both")
    limits=[]; limitations=[]; trace=[]
    if data.breaker_in_a is not None:
        _positive("breaker_in_a",data.breaker_in_a); limits.append(ConstraintLimit("breaker",data.breaker_in_a,f"Selected breaker rating In = {data.breaker_in_a:.1f} A")); limitations.append("Breaker rating is treated as a numerical ceiling only; current IEC 60364-4-43 protection verification is not yet implemented.")
    if data.connection_option_id is not None:
        option=get_connection_option(data.connection_option_id)
        if option.phase != data.phase: raise ValueError("Selected connection option phase does not match the supply phase")
        limitations.append(f"Connection evidence: {option.evidence_status}. Exact accessory configuration and product compliance remain to be verified.")
        if option.rating_a is not None:
            limits.append(ConstraintLimit("connection/outlet",option.rating_a,f"{option.label} nominal rating = {option.rating_a:.1f} A"))
        else: trace.append(f"{option.label}: no generic current ceiling assigned; not used as a numerical limit.")
    elif data.connection_rating_a is not None:
        _positive("connection_rating_a",data.connection_rating_a); limits.append(ConstraintLimit("connection/outlet",data.connection_rating_a,f"User-supplied connection/outlet rating = {data.connection_rating_a:.1f} A")); limitations.append("Connection/outlet rating is user-supplied; product/standard-specific suitability is not independently verified.")
    if data.ampacity_route is not None:
        amp=calculate_routed_ampacity(data.ampacity_route)
        if amp.iz_a is None: limitations.extend(amp.missing_or_unsupported); trace.append("Cable ampacity could not be verified for the supplied conditions.")
        else: limits.append(ConstraintLimit("cable ampacity",amp.iz_a,f"Verified cable Iz = {amp.iz_a:.1f} A")); trace.append(f"Cable ampacity limit Iz = {amp.iz_a:.3f} A")
    if data.length_m is not None:
        _positive("length_m",data.length_m)
        if data.voltage_drop_cross_section_mm2 is None or data.voltage_drop_material is None: limitations.append("Voltage-drop geometry/material is required to derive a voltage-drop load limit.")
        elif data.permitted_voltage_drop_percent is None or not data.voltage_drop_limit_source: limitations.append("A permitted voltage-drop limit and source are required to derive a voltage-drop load limit.")
        else:
            probe=calculate_voltage_drop(current_a=1.0,length_m=data.length_m,cross_section_mm2=data.voltage_drop_cross_section_mm2,system_voltage_v=data.voltage_v,phase=data.phase,material=data.voltage_drop_material,power_factor=data.power_factor,permitted_limit_percent=data.permitted_voltage_drop_percent,limit_source=data.voltage_drop_limit_source,allow_annex_g_defaults=data.allow_annex_g_defaults)
            if probe.voltage_drop_percent <= 0: limitations.append("Voltage-drop current limit could not be derived from the supplied model.")
            else:
                vd_limit_a=data.permitted_voltage_drop_percent/probe.voltage_drop_percent; limits.append(ConstraintLimit("voltage drop",vd_limit_a,f"Current producing {data.permitted_voltage_drop_percent:.2f}% drop = {vd_limit_a:.1f} A")); trace.extend((f"Voltage drop at 1 A = {probe.voltage_drop_percent:.6f}%",f"Voltage-drop current limit = {data.permitted_voltage_drop_percent:.6f} / {probe.voltage_drop_percent:.6f} = {vd_limit_a:.3f} A"))
    if not limits:
        limitations.append("At least one supported current-limiting constraint is required."); return MaxLoadResult("NOT VERIFIED",None,None,None,None,tuple(),tuple(dict.fromkeys(limitations)),tuple(trace))
    limiting=min(limits,key=lambda x:x.current_a); max_i=limiting.current_a; max_kw=_kw_from_current(max_i,data.voltage_v,data.phase,data.power_factor); max_kva=_kva_from_current(max_i,data.voltage_v,data.phase)
    trace.extend(("Effective current limit = minimum of supported constraints: "+", ".join(f"{x.name} {x.current_a:.1f} A" for x in limits),f"Limiting constraint = {limiting.name} at {max_i:.3f} A",f"Maximum apparent load = {max_kva:.3f} kVA",f"Maximum active load at PF {data.power_factor:.3f} = {max_kw:.3f} kW"))
    return MaxLoadResult("RESULT",max_i,max_kw,max_kva,limiting.name,tuple(limits),tuple(dict.fromkeys(limitations)),tuple(trace))
