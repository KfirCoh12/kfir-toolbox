"""Initial board-planning intelligence over the reusable circuit engine.

The board layer calculates every consumer through the shared circuit engine and
provides conservative phase-allocation and incomer-planning helpers. It intentionally
does not yet perform board-level diversity, protection verification, pole/way
allocation, selectivity, or phase-imbalance compliance checks.
"""
from dataclasses import dataclass
from math import isclose, isfinite
from typing import Literal

from .catalogs import BREAKER_RATINGS_A
from .circuit_engine import (
    CircuitDesignRequest,
    CircuitDesignResult,
    calculate_circuit_design,
)

BoardScopeStatus = Literal["SUPPORTED_SCOPE", "PARTIAL_SCOPE", "NOT_VERIFIED"]
BoardPhase = Literal["L1", "L2", "L3"]
SchedulePhase = Literal["L1", "L2", "L3", "3P"]
IncomerCandidateStatus = Literal["CANDIDATE", "NO_CANDIDATE"]


@dataclass(frozen=True)
class BoardPlanRequest:
    board_id: str
    description: str
    circuits: tuple[CircuitDesignRequest, ...]
    line_to_line_voltage_v: float = 400.0
    line_to_neutral_voltage_v: float = 230.0


@dataclass(frozen=True)
class BoardPhaseAllocation:
    circuit_id: str
    assigned_phase: SchedulePhase
    design_current_a: float


@dataclass(frozen=True)
class BoardPhaseBalance:
    l1_current_a: float
    l2_current_a: float
    l3_current_a: float
    spread_a: float
    allocations: tuple[BoardPhaseAllocation, ...]

    @property
    def max_phase_current_a(self) -> float:
        return max(self.l1_current_a, self.l2_current_a, self.l3_current_a)

    @property
    def min_phase_current_a(self) -> float:
        return min(self.l1_current_a, self.l2_current_a, self.l3_current_a)


@dataclass(frozen=True)
class BoardIncomerCandidate:
    status: IncomerCandidateStatus
    required_current_a: float
    breaker_rating_a: float | None
    basis: str


@dataclass(frozen=True)
class BoardCircuitScheduleRow:
    circuit_id: str
    description: str
    phase: Literal["single", "three"]
    assigned_phase: SchedulePhase
    load_type: Literal["kw", "kva", "a"]
    load_value: float
    demand_factor: float
    material: Literal["copper", "aluminium"]
    design_current_a: float
    breaker_a: float | None
    cable_mm2: float | None
    cable_runs: int | None
    connection_rating_a: float | None
    scope_status: BoardScopeStatus
    blocking_issue_codes: tuple[str, ...]


@dataclass(frozen=True)
class BoardPlanResult:
    request: BoardPlanRequest
    circuits: tuple[CircuitDesignResult, ...]
    scope_status: BoardScopeStatus
    phase_balance: BoardPhaseBalance
    incomer_candidate: BoardIncomerCandidate

    @property
    def circuit_count(self) -> int:
        return len(self.circuits)

    @property
    def blocking_circuit_ids(self) -> tuple[str, ...]:
        return tuple(
            circuit.request.circuit_id
            for circuit in self.circuits
            if circuit.verification.blocking_issues
        )

    @property
    def schedule_rows(self) -> tuple[BoardCircuitScheduleRow, ...]:
        assigned = {
            allocation.circuit_id: allocation.assigned_phase
            for allocation in self.phase_balance.allocations
        }
        return tuple(
            BoardCircuitScheduleRow(
                circuit_id=circuit.request.circuit_id,
                description=circuit.request.description,
                phase=circuit.request.phase,
                assigned_phase=assigned[circuit.request.circuit_id],
                load_type=circuit.request.load_type,
                load_value=circuit.request.load_value,
                demand_factor=circuit.request.demand_factor,
                material=circuit.request.material,
                design_current_a=circuit.design_current_a,
                breaker_a=circuit.breaker_a,
                cable_mm2=circuit.cable_mm2,
                cable_runs=circuit.cable_runs,
                connection_rating_a=circuit.connection_rating_a,
                scope_status=circuit.verification.scope_status,
                blocking_issue_codes=tuple(
                    issue.code for issue in circuit.verification.blocking_issues
                ),
            )
            for circuit in self.circuits
        )

    @property
    def phase_balancing_implemented(self) -> bool:
        return True

    @property
    def incomer_candidate_implemented(self) -> bool:
        return True

    @property
    def board_level_checks_implemented(self) -> bool:
        """No board rating/diversity/selectivity compliance checks are active yet."""
        return False


def _board_scope(circuits: tuple[CircuitDesignResult, ...]) -> BoardScopeStatus:
    if any(c.verification.scope_status == "NOT_VERIFIED" for c in circuits):
        return "NOT_VERIFIED"
    if any(
        c.verification.scope_status == "PARTIAL_SCOPE"
        or c.verification.blocking_issues
        for c in circuits
    ):
        return "PARTIAL_SCOPE"
    return "SUPPORTED_SCOPE"


def _validate_board_system(data: BoardPlanRequest) -> None:
    for name, value in (
        ("line_to_line_voltage_v", data.line_to_line_voltage_v),
        ("line_to_neutral_voltage_v", data.line_to_neutral_voltage_v),
    ):
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a finite value greater than 0")

    for circuit in data.circuits:
        expected = (
            data.line_to_line_voltage_v
            if circuit.phase == "three"
            else data.line_to_neutral_voltage_v
        )
        if not isclose(circuit.voltage_v, expected, rel_tol=0.0, abs_tol=1e-9):
            voltage_kind = "line-to-line" if circuit.phase == "three" else "line-to-neutral"
            raise ValueError(
                f"Circuit {circuit.circuit_id} voltage {circuit.voltage_v:g} V does not match "
                f"the board {voltage_kind} voltage {expected:g} V"
            )


def _balance_phases(
    circuits: tuple[CircuitDesignResult, ...],
) -> BoardPhaseBalance:
    """Allocate single-phase circuits using a deterministic largest-first heuristic.

    Three-phase design current is treated as an equal per-phase contribution. Single-
    phase circuits are sorted by descending design current and each is placed on the
    phase with the lowest accumulated current. Ties resolve L1, then L2, then L3.

    This is a planning heuristic only. No acceptable imbalance threshold or standards
    compliance claim is introduced here.
    """
    phase_currents: dict[BoardPhase, float] = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
    allocations: list[BoardPhaseAllocation] = []

    for circuit in circuits:
        if circuit.request.phase == "three":
            current = circuit.design_current_a
            for phase in ("L1", "L2", "L3"):
                phase_currents[phase] += current
            allocations.append(BoardPhaseAllocation(
                circuit_id=circuit.request.circuit_id,
                assigned_phase="3P",
                design_current_a=current,
            ))

    single_phase = sorted(
        (c for c in circuits if c.request.phase == "single"),
        key=lambda c: (-c.design_current_a, c.request.circuit_id),
    )
    phase_order: tuple[BoardPhase, ...] = ("L1", "L2", "L3")
    for circuit in single_phase:
        assigned = min(phase_order, key=lambda phase: phase_currents[phase])
        phase_currents[assigned] += circuit.design_current_a
        allocations.append(BoardPhaseAllocation(
            circuit_id=circuit.request.circuit_id,
            assigned_phase=assigned,
            design_current_a=circuit.design_current_a,
        ))

    allocation_by_id = {a.circuit_id: a for a in allocations}
    ordered_allocations = tuple(
        allocation_by_id[c.request.circuit_id] for c in circuits
    )
    currents = tuple(phase_currents[phase] for phase in phase_order)
    return BoardPhaseBalance(
        l1_current_a=phase_currents["L1"],
        l2_current_a=phase_currents["L2"],
        l3_current_a=phase_currents["L3"],
        spread_a=max(currents) - min(currents),
        allocations=ordered_allocations,
    )


def _suggest_incomer(balance: BoardPhaseBalance) -> BoardIncomerCandidate:
    required = balance.max_phase_current_a
    rating = next((float(x) for x in BREAKER_RATINGS_A if x >= required), None)
    basis = (
        "First declared breaker rating at or above the highest planned phase current. "
        "Circuit demand factors are already reflected in their design currents; no additional "
        "board-level diversity or IEC protection verification is applied."
    )
    return BoardIncomerCandidate(
        status="CANDIDATE" if rating is not None else "NO_CANDIDATE",
        required_current_a=required,
        breaker_rating_a=rating,
        basis=basis,
    )


def calculate_board_plan(data: BoardPlanRequest) -> BoardPlanResult:
    """Calculate board circuits and produce conservative planning outputs."""
    board_id = data.board_id.strip()
    description = data.description.strip()
    if not board_id:
        raise ValueError("board_id is required")
    if not description:
        raise ValueError("description is required")
    if not data.circuits:
        raise ValueError("at least one circuit is required")

    circuit_ids = [c.circuit_id.strip() for c in data.circuits]
    if len(circuit_ids) != len(set(circuit_ids)):
        raise ValueError("circuit_id values must be unique within a board")

    _validate_board_system(data)
    circuits = tuple(calculate_circuit_design(circuit) for circuit in data.circuits)
    phase_balance = _balance_phases(circuits)
    return BoardPlanResult(
        request=data,
        circuits=circuits,
        scope_status=_board_scope(circuits),
        phase_balance=phase_balance,
        incomer_candidate=_suggest_incomer(phase_balance),
    )
