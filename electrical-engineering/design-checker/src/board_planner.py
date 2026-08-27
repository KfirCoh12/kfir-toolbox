"""Initial board-planning aggregation over the reusable circuit engine.

V0 intentionally does not perform board-level diversity, incomer sizing, phase
balancing, pole/way allocation, or selectivity. It establishes the board/circuit
contract and runs each consumer through the existing circuit intelligence.
"""
from dataclasses import dataclass
from typing import Literal

from .circuit_engine import (
    CircuitDesignRequest,
    CircuitDesignResult,
    calculate_circuit_design,
)

BoardScopeStatus = Literal["SUPPORTED_SCOPE", "PARTIAL_SCOPE", "NOT_VERIFIED"]


@dataclass(frozen=True)
class BoardPlanRequest:
    board_id: str
    description: str
    circuits: tuple[CircuitDesignRequest, ...]


@dataclass(frozen=True)
class BoardPlanResult:
    request: BoardPlanRequest
    circuits: tuple[CircuitDesignResult, ...]
    scope_status: BoardScopeStatus

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
    def board_level_checks_implemented(self) -> bool:
        """Explicit V0 guard: board-level engineering intelligence is not active yet."""
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


def calculate_board_plan(data: BoardPlanRequest) -> BoardPlanResult:
    """Calculate each board circuit independently using the shared circuit engine."""
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

    circuits = tuple(calculate_circuit_design(circuit) for circuit in data.circuits)
    return BoardPlanResult(
        request=data,
        circuits=circuits,
        scope_status=_board_scope(circuits),
    )
