"""Reusable circuit-design facade for calculators and future board planning.

This layer does not introduce new engineering rules. It packages the existing
circuit selector and structured verification result into a stable, named circuit
contract that higher-level tools can consume without depending on UI state.
"""
from dataclasses import dataclass
from typing import Literal

from .circuit_selector import CircuitSelectionInput, CircuitSelectionResult, select_circuit
from .verification import ResultVerification, summarize_circuit_selection_verification

Material = Literal["copper", "aluminium"]
Phase = Literal["single", "three"]
LoadType = Literal["kw", "kva", "a"]


@dataclass(frozen=True)
class CircuitDesignRequest:
    circuit_id: str
    description: str
    load_type: LoadType
    load_value: float
    voltage_v: float
    phase: Phase
    power_factor: float | None
    demand_factor: float = 1.0
    material: Material = "copper"
    ambient_temperature_c: float = 30.0
    grouped_circuits: int = 1
    grouping_arrangement: str | None = None
    parallel_runs: int = 1
    equal_current_sharing_confirmed: bool | None = None
    length_m: float | None = None
    permitted_voltage_drop_percent: float | None = None
    voltage_drop_limit_source: str | None = None
    allow_annex_g_defaults: bool = False


@dataclass(frozen=True)
class CircuitDesignResult:
    request: CircuitDesignRequest
    selection: CircuitSelectionResult
    verification: ResultVerification

    @property
    def design_current_a(self) -> float:
        return self.selection.current.design_current_a

    @property
    def breaker_a(self) -> float | None:
        return self.selection.suggested_breaker_a

    @property
    def cable_mm2(self) -> float | None:
        return self.selection.suggested_cable_mm2

    @property
    def cable_iz_a(self) -> float | None:
        return self.selection.cable_iz_a

    @property
    def cable_runs(self) -> int | None:
        return self.selection.suggested_parallel_runs

    @property
    def voltage_drop_percent(self) -> float | None:
        if self.selection.voltage_drop is None:
            return None
        return self.selection.voltage_drop.voltage_drop_percent

    @property
    def connection_id(self) -> str | None:
        if self.selection.suggested_connection is None:
            return None
        return self.selection.suggested_connection.id

    @property
    def connection_rating_a(self) -> float | None:
        if self.selection.suggested_connection is None:
            return None
        return self.selection.suggested_connection.rating_a


def calculate_circuit_design(data: CircuitDesignRequest) -> CircuitDesignResult:
    """Run one named circuit through the existing selector and verification layer."""
    circuit_id = data.circuit_id.strip()
    description = data.description.strip()
    if not circuit_id:
        raise ValueError("circuit_id is required")
    if not description:
        raise ValueError("description is required")

    selection = select_circuit(CircuitSelectionInput(
        load_type=data.load_type,
        load_value=data.load_value,
        voltage_v=data.voltage_v,
        phase=data.phase,
        power_factor=data.power_factor,
        demand_factor=data.demand_factor,
        material=data.material,
        ambient_temperature_c=data.ambient_temperature_c,
        grouped_circuits=data.grouped_circuits,
        grouping_arrangement=data.grouping_arrangement,
        parallel_runs=data.parallel_runs,
        equal_current_sharing_confirmed=data.equal_current_sharing_confirmed,
        length_m=data.length_m,
        permitted_voltage_drop_percent=data.permitted_voltage_drop_percent,
        voltage_drop_limit_source=data.voltage_drop_limit_source,
        allow_annex_g_defaults=data.allow_annex_g_defaults,
    ))
    verification = summarize_circuit_selection_verification(selection)
    return CircuitDesignResult(data, selection, verification)
