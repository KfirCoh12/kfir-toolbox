"""Auto/manual final-branch facade for board planning.

AUTO means a known expected load drives the existing forward circuit selector.
MANUAL means the user has fixed a supported rated connection/outlet; its nominal
current becomes the required branch capacity and is passed through the same selector.
No new breaker/cable sizing formulas are introduced here.
"""
from dataclasses import dataclass
from typing import Literal

from .circuit_engine import CircuitDesignRequest, CircuitDesignResult, calculate_circuit_design
from .connection import ConnectionOption, get_connection_option

BranchMode = Literal["auto", "manual"]
Phase = Literal["single", "three"]
Material = Literal["copper", "aluminium"]


@dataclass(frozen=True)
class FinalBranchDesignRequest:
    circuit_id: str
    description: str
    mode: BranchMode
    voltage_v: float
    phase: Phase
    material: Material = "copper"
    expected_load_kw: float | None = None
    connection_option_id: str | None = None
    power_factor: float = 0.9
    demand_factor: float = 1.0
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
class FinalBranchDesignResult:
    request: FinalBranchDesignRequest
    circuit: CircuitDesignResult
    fixed_connection: ConnectionOption | None

    @property
    def design_current_a(self) -> float:
        return self.circuit.design_current_a

    @property
    def breaker_a(self) -> float | None:
        return self.circuit.breaker_a

    @property
    def cable_mm2(self) -> float | None:
        return self.circuit.cable_mm2

    @property
    def cable_runs(self) -> int | None:
        return self.circuit.cable_runs

    @property
    def connection(self) -> ConnectionOption | None:
        if self.fixed_connection is not None:
            return self.fixed_connection
        return self.circuit.selection.suggested_connection

    @property
    def connection_rating_a(self) -> float | None:
        connection = self.connection
        return connection.rating_a if connection is not None else None


def _base_request(
    data: FinalBranchDesignRequest,
    *,
    load_type: Literal["kw", "a"],
    load_value: float,
) -> CircuitDesignRequest:
    return CircuitDesignRequest(
        circuit_id=data.circuit_id,
        description=data.description,
        load_type=load_type,
        load_value=load_value,
        voltage_v=data.voltage_v,
        phase=data.phase,
        power_factor=data.power_factor,
        demand_factor=data.demand_factor if load_type == "kw" else 1.0,
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
    )


def calculate_final_branch(data: FinalBranchDesignRequest) -> FinalBranchDesignResult:
    """Design one final branch from either a load or a fixed rated connection."""
    if data.mode == "auto":
        if data.expected_load_kw is None:
            raise ValueError("expected_load_kw is required in auto mode")
        if data.connection_option_id is not None:
            raise ValueError("connection_option_id must not be supplied in auto mode")
        circuit = calculate_circuit_design(
            _base_request(data, load_type="kw", load_value=data.expected_load_kw)
        )
        return FinalBranchDesignResult(data, circuit, None)

    if data.mode != "manual":
        raise ValueError("mode must be auto or manual")
    if data.connection_option_id is None:
        raise ValueError("connection_option_id is required in manual mode")
    if data.expected_load_kw is not None:
        raise ValueError("expected_load_kw must not be supplied in manual mode")

    connection = get_connection_option(data.connection_option_id)
    if connection.phase != data.phase:
        raise ValueError("selected connection phase does not match branch phase")
    if connection.rating_a is None:
        raise ValueError(
            "manual branch mode requires a connection with a declared nominal current rating"
        )

    circuit = calculate_circuit_design(
        _base_request(data, load_type="a", load_value=connection.rating_a)
    )
    return FinalBranchDesignResult(data, circuit, connection)
