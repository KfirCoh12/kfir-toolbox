"""Conservative V0.6 automatic circuit selection over explicitly supported data."""
from dataclasses import dataclass, replace
from typing import Literal

from .ampacity_data import BASE_IZ_METHOD_E_3_LOADED
from .cable import CableAmpacityInput, calculate_supported_iz
from .connection import ConnectionOption, suggest_connection
from .current import CurrentResult, calculate_design_current
from .voltage_drop import VoltageDropResult, calculate_voltage_drop

Material = Literal["copper", "aluminium"]
STANDARD_BREAKER_CANDIDATES_A = (6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630)

@dataclass(frozen=True)
class CircuitSelectionInput:
    load_type: Literal["kw", "kva", "a"]
    load_value: float
    voltage_v: float
    phase: Literal["single", "three"]
    power_factor: float | None
    demand_factor: float = 1.0
    material: Material = "copper"
    ambient_temperature_c: float = 30.0
    grouped_circuits: int = 1
    grouping_arrangement: str | None = None
    length_m: float | None = None
    permitted_voltage_drop_percent: float | None = None
    voltage_drop_limit_source: str | None = None
    allow_annex_g_defaults: bool = False

@dataclass(frozen=True)
class CircuitSelectionResult:
    status: Literal["SUGGESTION", "NO SUPPORTED SOLUTION", "NOT VERIFIED"]
    current: CurrentResult
    suggested_breaker_a: float | None
    suggested_cable_mm2: float | None
    cable_iz_a: float | None
    suggested_connection: ConnectionOption | None
    voltage_drop: VoltageDropResult | None
    rejected_candidates: tuple[str, ...]
    limitations: tuple[str, ...]
    trace: tuple[str, ...]

def _first_breaker_at_or_above(ib_a: float) -> float | None:
    return next((float(x) for x in STANDARD_BREAKER_CANDIDATES_A if x >= ib_a), None)

def select_circuit(data: CircuitSelectionInput) -> CircuitSelectionResult:
    current = calculate_design_current(load_type=data.load_type, load_value=data.load_value, voltage_v=data.voltage_v, phase=data.phase, power_factor=data.power_factor, demand_factor=data.demand_factor)
    ib = current.design_current_a
    breaker = _first_breaker_at_or_above(ib)
    limitations = ["Breaker candidate is a conventional rating suggestion only; IEC 60364-4-43 protection verification is not yet implemented."]
    trace = [f"Design current Ib = {ib:.3f} A"]
    if breaker is None:
        return CircuitSelectionResult("NO SUPPORTED SOLUTION", current, None, None, None, None, None, tuple(), tuple(limitations), tuple(trace + ["No breaker candidate in the declared V0.6 set is >= Ib."]))
    trace.append(f"First declared breaker candidate >= Ib: {breaker:.0f} A")
    connection = suggest_connection(phase=data.phase, required_current_a=breaker)
    limitations.append(f"Connection rating evidence: {connection.evidence_status}.")
    trace.append(f"Connection suggestion for {breaker:.0f} A requirement: {connection.label}")
    if data.phase != "three":
        limitations.append("Automatic cable selection currently supports three-phase / three-loaded-conductor Method E cases only.")
        return CircuitSelectionResult("NOT VERIFIED", current, breaker, None, None, connection, None, tuple(), tuple(dict.fromkeys(limitations)), tuple(trace))

    rejected=[]
    sizes=sorted(BASE_IZ_METHOD_E_3_LOADED.get(data.material, {}).keys())
    for size in sizes:
        amp=calculate_supported_iz(CableAmpacityInput(material=data.material,cross_section_mm2=size,insulation="xlpe_epr",loaded_conductors=3,installation_method="E",environment="air",ambient_temperature_c=data.ambient_temperature_c,grouped_circuits=data.grouped_circuits,grouping_arrangement=data.grouping_arrangement,parallel_runs=1,thdi_percent=0.0,neutral_loaded=False))
        if amp.iz_a is None:
            rejected.append(f"{size:g} mm²: ampacity not verified for supplied conditions"); continue
        if amp.iz_a < breaker:
            rejected.append(f"{size:g} mm²: Iz {amp.iz_a:.1f} A < suggested In {breaker:.0f} A"); continue
        vd=None
        if data.length_m is not None:
            vd=calculate_voltage_drop(current_a=ib,length_m=data.length_m,cross_section_mm2=size,system_voltage_v=data.voltage_v,phase=data.phase,material=data.material,power_factor=data.power_factor,permitted_limit_percent=data.permitted_voltage_drop_percent,limit_source=data.voltage_drop_limit_source,allow_annex_g_defaults=data.allow_annex_g_defaults)
            if vd.comparison == "FAIL":
                rejected.append(f"{size:g} mm²: voltage drop {vd.voltage_drop_percent:.2f}% exceeds {data.permitted_voltage_drop_percent:.2f}%"); continue
            if vd.comparison == "NO LIMIT CHECKED": limitations.append("Voltage drop was calculated but no sourced permitted limit was checked.")
        trace.append(f"Selected first supported cable candidate: {size:g} mm², Iz = {amp.iz_a:.1f} A")
        return CircuitSelectionResult("SUGGESTION", current, breaker, size, amp.iz_a, connection, vd, tuple(rejected), tuple(dict.fromkeys(limitations)), tuple(trace))

    return CircuitSelectionResult("NO SUPPORTED SOLUTION", current, breaker, None, None, connection, None, tuple(rejected), tuple(dict.fromkeys(limitations)), tuple(trace + ["No cable in the explicit V0.6 dataset passed all requested checks."]))

@dataclass(frozen=True)
class CircuitMaterialOptionsResult:
    copper: CircuitSelectionResult
    aluminium: CircuitSelectionResult


def select_material_options(data: CircuitSelectionInput) -> CircuitMaterialOptionsResult:
    """Run the same design case for both supported conductor materials.

    This intentionally does not choose a winner: material choice can depend on
    cost, terminations and project practice that are outside the kW/A/cable
    relationship. Each option is independently checked by the same engine.
    """
    return CircuitMaterialOptionsResult(
        copper=select_circuit(replace(data, material="copper")),
        aluminium=select_circuit(replace(data, material="aluminium")),
    )
