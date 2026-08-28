"""Initial board-planning intelligence over the reusable circuit engine.

The board layer calculates every local consumer through the shared circuit engine and
provides conservative phase-allocation and incomer-planning helpers. It can also
accept explicit downstream phase-current contributions so hierarchical boards can be
rolled up without flattening their child circuits or inventing a balanced equivalent.

It intentionally does not yet perform board-level diversity, protection verification,
pole/way allocation, selectivity, or phase-imbalance compliance checks.
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
class BoardPhasePreference:
    circuit_id: str
    phase: BoardPhase


@dataclass(frozen=True)
class BoardPhaseContribution:
    """An already-derived downstream current vector seen by this board.

    This is not a final circuit and therefore does not appear in the local circuit
    schedule. It preserves phase imbalance from a downstream calculation boundary.
    The basis text is mandatory so an upstream plan never loses provenance.
    """

    contribution_id: str
    l1_current_a: float
    l2_current_a: float
    l3_current_a: float
    basis: str

    @property
    def max_phase_current_a(self) -> float:
        return max(self.l1_current_a, self.l2_current_a, self.l3_current_a)


@dataclass(frozen=True)
class BoardPlanRequest:
    board_id: str
    description: str
    circuits: tuple[CircuitDesignRequest, ...]
    line_to_line_voltage_v: float = 400.0
    line_to_neutral_voltage_v: float = 230.0
    phase_preferences: tuple[BoardPhasePreference, ...] = tuple()
    phase_contributions: tuple[BoardPhaseContribution, ...] = tuple()


@dataclass(frozen=True)
class BoardPhaseAllocation:
    circuit_id: str
    assigned_phase: SchedulePhase
    design_current_a: float
    locked: bool = False


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
    phase_locked: bool
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
            allocation.circuit_id: allocation
            for allocation in self.phase_balance.allocations
        }
        return tuple(
            BoardCircuitScheduleRow(
                circuit_id=circuit.request.circuit_id,
                description=circuit.request.description,
                phase=circuit.request.phase,
                assigned_phase=assigned[circuit.request.circuit_id].assigned_phase,
                phase_locked=assigned[circuit.request.circuit_id].locked,
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


def _board_scope(
    circuits: tuple[CircuitDesignResult, ...],
    phase_contributions: tuple[BoardPhaseContribution, ...],
) -> BoardScopeStatus:
    if any(c.verification.scope_status == "NOT_VERIFIED" for c in circuits):
        return "NOT_VERIFIED"
    if phase_contributions:
        return "PARTIAL_SCOPE"
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


def _validate_phase_preferences(data: BoardPlanRequest) -> dict[str, BoardPhase]:
    circuit_by_id = {c.circuit_id.strip(): c for c in data.circuits}
    preferences: dict[str, BoardPhase] = {}
    for preference in data.phase_preferences:
        circuit_id = preference.circuit_id.strip()
        if not circuit_id:
            raise ValueError("phase preference circuit_id is required")
        if preference.phase not in ("L1", "L2", "L3"):
            raise ValueError("phase preference must be L1, L2 or L3")
        if circuit_id in preferences:
            raise ValueError(f"duplicate phase preference for circuit {circuit_id}")
        circuit = circuit_by_id.get(circuit_id)
        if circuit is None:
            raise ValueError(f"phase preference references unknown circuit {circuit_id}")
        if circuit.phase != "single":
            raise ValueError(
                f"phase preference can only be applied to a single-phase circuit: {circuit_id}"
            )
        preferences[circuit_id] = preference.phase
    return preferences


def _validate_phase_contributions(
    data: BoardPlanRequest,
) -> tuple[BoardPhaseContribution, ...]:
    seen: set[str] = set()
    validated: list[BoardPhaseContribution] = []
    for contribution in data.phase_contributions:
        contribution_id = contribution.contribution_id.strip()
        if not contribution_id:
            raise ValueError("phase contribution contribution_id is required")
        if contribution_id in seen:
            raise ValueError(f"duplicate phase contribution {contribution_id}")
        seen.add(contribution_id)
        values = (
            contribution.l1_current_a,
            contribution.l2_current_a,
            contribution.l3_current_a,
        )
        if any(not isfinite(value) or value < 0 for value in values):
            raise ValueError(
                f"phase contribution {contribution_id} currents must be finite and at least 0"
            )
        if max(values) <= 0:
            raise ValueError(
                f"phase contribution {contribution_id} must contain a current greater than 0"
            )
        if not contribution.basis.strip():
            raise ValueError(f"phase contribution {contribution_id} basis is required")
        validated.append(contribution)
    return tuple(validated)


def _balance_phases(
    circuits: tuple[CircuitDesignResult, ...],
    preferences: dict[str, BoardPhase],
    phase_contributions: tuple[BoardPhaseContribution, ...],
) -> BoardPhaseBalance:
    """Allocate local single-phase circuits around locked downstream phase demand.

    Explicit downstream contributions are applied first and preserve their L1/L2/L3
    current vector. Three-phase local circuits then contribute equally on all phases.
    Locked local single-phase circuits are applied next. Remaining single-phase
    circuits are sorted by descending design current and placed on the phase with the
    lowest accumulated current. Ties resolve L1, then L2, then L3.

    This is a planning heuristic only. No acceptable imbalance threshold or standards
    compliance claim is introduced here.
    """
    phase_currents: dict[BoardPhase, float] = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
    allocations: list[BoardPhaseAllocation] = []

    for contribution in phase_contributions:
        phase_currents["L1"] += contribution.l1_current_a
        phase_currents["L2"] += contribution.l2_current_a
        phase_currents["L3"] += contribution.l3_current_a

    for circuit in circuits:
        if circuit.request.phase == "three":
            current = circuit.design_current_a
            for phase in ("L1", "L2", "L3"):
                phase_currents[phase] += current
            allocations.append(BoardPhaseAllocation(
                circuit_id=circuit.request.circuit_id,
                assigned_phase="3P",
                design_current_a=current,
                locked=True,
            ))

    single_phase = tuple(c for c in circuits if c.request.phase == "single")
    for circuit in single_phase:
        circuit_id = circuit.request.circuit_id.strip()
        if circuit_id not in preferences:
            continue
        assigned = preferences[circuit_id]
        phase_currents[assigned] += circuit.design_current_a
        allocations.append(BoardPhaseAllocation(
            circuit_id=circuit.request.circuit_id,
            assigned_phase=assigned,
            design_current_a=circuit.design_current_a,
            locked=True,
        ))

    unlocked = sorted(
        (c for c in single_phase if c.request.circuit_id.strip() not in preferences),
        key=lambda c: (-c.design_current_a, c.request.circuit_id),
    )
    phase_order: tuple[BoardPhase, ...] = ("L1", "L2", "L3")
    for circuit in unlocked:
        assigned = min(phase_order, key=lambda phase: phase_currents[phase])
        phase_currents[assigned] += circuit.design_current_a
        allocations.append(BoardPhaseAllocation(
            circuit_id=circuit.request.circuit_id,
            assigned_phase=assigned,
            design_current_a=circuit.design_current_a,
            locked=False,
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


def _suggest_incomer(
    balance: BoardPhaseBalance,
    has_phase_contributions: bool,
) -> BoardIncomerCandidate:
    required = balance.max_phase_current_a
    rating = next((float(x) for x in BREAKER_RATINGS_A if x >= required), None)
    contribution_note = (
        " Explicit downstream phase contributions are included without additional diversity."
        if has_phase_contributions
        else ""
    )
    basis = (
        "First declared breaker rating at or above the highest planned phase current. "
        "Circuit demand factors are already reflected in their design currents; no additional "
        "board-level diversity or IEC protection verification is applied."
        + contribution_note
    )
    return BoardIncomerCandidate(
        status="CANDIDATE" if rating is not None else "NO_CANDIDATE",
        required_current_a=required,
        breaker_rating_a=rating,
        basis=basis,
    )


def calculate_board_plan(data: BoardPlanRequest) -> BoardPlanResult:
    """Calculate local board circuits plus explicit downstream phase contributions."""
    board_id = data.board_id.strip()
    description = data.description.strip()
    if not board_id:
        raise ValueError("board_id is required")
    if not description:
        raise ValueError("description is required")
    if not data.circuits and not data.phase_contributions:
        raise ValueError("at least one circuit or phase contribution is required")

    circuit_ids = [c.circuit_id.strip() for c in data.circuits]
    if len(circuit_ids) != len(set(circuit_ids)):
        raise ValueError("circuit_id values must be unique within a board")

    _validate_board_system(data)
    preferences = _validate_phase_preferences(data)
    contributions = _validate_phase_contributions(data)
    circuits = tuple(calculate_circuit_design(circuit) for circuit in data.circuits)
    phase_balance = _balance_phases(circuits, preferences, contributions)
    return BoardPlanResult(
        request=data,
        circuits=circuits,
        scope_status=_board_scope(circuits, contributions),
        phase_balance=phase_balance,
        incomer_candidate=_suggest_incomer(phase_balance, bool(contributions)),
    )
