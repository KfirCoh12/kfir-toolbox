"""Bottom-up planning across nested board calculation boundaries.

Each board remains an independent calculation boundary. A downstream board's actual
L1/L2/L3 current vector is propagated to its parent as a BoardPhaseContribution,
not flattened into the parent's local circuit list and not replaced by a fictitious
balanced three-phase load.

Callers may also supply exact CircuitDesignRequest overrides for graph loads whose
real basis is fixed current or kVA. The hierarchy therefore preserves that basis
without converting it to an invented kW value.
"""
from dataclasses import dataclass, replace
from typing import Literal

from .board_boundaries import BoardCalculationBoundary, calculation_boundaries_from_graph
from .board_graph import BoardElectricalGraph, validate_board_graph
from .board_planner import (
    BoardPhaseContribution,
    BoardPlanRequest,
    BoardPlanResult,
    calculate_board_plan,
)
from .catalogs import BREAKER_RATINGS_A
from .circuit_engine import CircuitDesignRequest

HierarchyBoardStatus = Literal["CALCULATED", "NO_DEMAND"]
FeederRollupStatus = Literal["PROVISIONAL", "NO_DEMAND", "NO_CANDIDATE"]


@dataclass(frozen=True)
class HierarchyBoardResult:
    board_id: str
    parent_board_id: str | None
    feeder_circuit_id: str | None
    status: HierarchyBoardStatus
    plan: BoardPlanResult | None
    child_board_ids: tuple[str, ...]


@dataclass(frozen=True)
class SubBoardFeederRollup:
    board_id: str
    parent_board_id: str
    feeder_circuit_id: str
    status: FeederRollupStatus
    l1_current_a: float
    l2_current_a: float
    l3_current_a: float
    required_current_a: float
    breaker_candidate_a: float | None
    basis: str
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class BoardHierarchyPlanResult:
    boards: tuple[HierarchyBoardResult, ...]
    feeder_rollups: tuple[SubBoardFeederRollup, ...]

    @property
    def plans(self) -> tuple[BoardPlanResult, ...]:
        return tuple(board.plan for board in self.boards if board.plan is not None)

    @property
    def plans_by_board_id(self) -> dict[str, BoardPlanResult]:
        return {
            board.board_id: board.plan
            for board in self.boards
            if board.plan is not None
        }

    @property
    def root(self) -> HierarchyBoardResult:
        roots = tuple(board for board in self.boards if board.parent_board_id is None)
        if len(roots) != 1:
            raise ValueError("hierarchy result must contain exactly one root board")
        return roots[0]


def _parent_board_id(
    graph: BoardElectricalGraph,
    boundary: BoardCalculationBoundary,
) -> str | None:
    if boundary.feeder_circuit_id is None:
        return None
    anchor = graph.node_by_id[boundary.anchor_node_id]
    if anchor.kind != "sub_board":
        raise ValueError(f"downstream board {boundary.board_id} anchor must be a sub_board")
    for ancestor in graph.ancestors_of(anchor.node_id):
        if ancestor.kind == "busbar" and ancestor.board_ref:
            return ancestor.board_ref.strip()
    raise ValueError(f"downstream board {boundary.board_id} has no parent board busbar")


def _base_request(
    graph: BoardElectricalGraph,
    boundary: BoardCalculationBoundary,
    contributions: tuple[BoardPhaseContribution, ...],
) -> BoardPlanRequest | None:
    if boundary.request is None and not contributions:
        return None
    if boundary.request is None:
        return BoardPlanRequest(
            board_id=boundary.board_id,
            description=boundary.description,
            circuits=tuple(),
            line_to_line_voltage_v=graph.line_to_line_voltage_v,
            line_to_neutral_voltage_v=graph.line_to_neutral_voltage_v,
            phase_contributions=contributions,
        )
    return replace(boundary.request, phase_contributions=contributions)


def _contribution_from_child(
    child_board_id: str,
    feeder_circuit_id: str,
    child_plan: BoardPlanResult,
) -> BoardPhaseContribution:
    balance = child_plan.phase_balance
    return BoardPhaseContribution(
        contribution_id=feeder_circuit_id,
        l1_current_a=balance.l1_current_a,
        l2_current_a=balance.l2_current_a,
        l3_current_a=balance.l3_current_a,
        basis=(
            f"Calculated downstream board {child_board_id} phase demand propagated "
            "without additional hierarchy-level diversity."
        ),
    )


def _feeder_rollup(board: HierarchyBoardResult) -> SubBoardFeederRollup:
    if board.parent_board_id is None or board.feeder_circuit_id is None:
        raise ValueError("root board does not have an upstream feeder rollup")
    if board.plan is None:
        return SubBoardFeederRollup(
            board_id=board.board_id,
            parent_board_id=board.parent_board_id,
            feeder_circuit_id=board.feeder_circuit_id,
            status="NO_DEMAND",
            l1_current_a=0.0,
            l2_current_a=0.0,
            l3_current_a=0.0,
            required_current_a=0.0,
            breaker_candidate_a=None,
            basis="Downstream board has no calculated local or child-board demand.",
            limitations=("No feeder demand is synthesized for an empty downstream board.",),
        )

    balance = board.plan.phase_balance
    required = balance.max_phase_current_a
    rating = next((float(value) for value in BREAKER_RATINGS_A if value >= required), None)
    return SubBoardFeederRollup(
        board_id=board.board_id,
        parent_board_id=board.parent_board_id,
        feeder_circuit_id=board.feeder_circuit_id,
        status="PROVISIONAL" if rating is not None else "NO_CANDIDATE",
        l1_current_a=balance.l1_current_a,
        l2_current_a=balance.l2_current_a,
        l3_current_a=balance.l3_current_a,
        required_current_a=required,
        breaker_candidate_a=rating,
        basis=(
            "Highest calculated downstream-board phase current, with no additional "
            "hierarchy-level diversity."
        ),
        limitations=(
            "Breaker rating is a conventional planning candidate only; protection and selectivity are not verified.",
            "Feeder cable is not sized because feeder material and installation conditions are not declared by the hierarchy model.",
            "L1/L2/L3 are assumed phase-aligned between parent and child boards; transformer phase shift is not modeled.",
        ),
    )


def calculate_board_hierarchy(
    graph: BoardElectricalGraph,
    circuit_request_overrides: tuple[CircuitDesignRequest, ...] = tuple(),
) -> BoardHierarchyPlanResult:
    """Calculate every board bottom-up and propagate child phase vectors upstream.

    Exact circuit overrides are passed into boundary construction before any board is
    solved. A fixed-A or kVA load therefore remains fixed-A or kVA at every hierarchy
    depth and in generated schedule rows.
    """
    validate_board_graph(graph)
    boundaries = calculation_boundaries_from_graph(graph, circuit_request_overrides)
    boundary_by_id = {boundary.board_id: boundary for boundary in boundaries}
    if len(boundary_by_id) != len(boundaries):
        raise ValueError("board calculation boundaries must have unique board_id values")

    parent_by_id = {
        boundary.board_id: _parent_board_id(graph, boundary)
        for boundary in boundaries
    }
    children_by_id: dict[str, list[str]] = {board_id: [] for board_id in boundary_by_id}
    for board_id, parent_id in parent_by_id.items():
        if parent_id is None:
            continue
        if parent_id not in boundary_by_id:
            raise ValueError(f"board {board_id} references unknown parent board {parent_id}")
        children_by_id[parent_id].append(board_id)

    roots = tuple(board_id for board_id, parent_id in parent_by_id.items() if parent_id is None)
    if len(roots) != 1 or roots[0] != graph.board_id.strip():
        raise ValueError("hierarchy must resolve exactly one root board matching graph.board_id")

    solved: dict[str, HierarchyBoardResult] = {}
    visiting: set[str] = set()

    def solve(board_id: str) -> HierarchyBoardResult:
        if board_id in solved:
            return solved[board_id]
        if board_id in visiting:
            raise ValueError("board hierarchy contains a board-boundary cycle")
        visiting.add(board_id)

        boundary = boundary_by_id[board_id]
        child_ids = tuple(children_by_id[board_id])
        contributions: list[BoardPhaseContribution] = []
        for child_id in child_ids:
            child = solve(child_id)
            if child.plan is None:
                continue
            if child.feeder_circuit_id is None:
                raise ValueError(f"downstream board {child_id} requires feeder_circuit_id")
            contributions.append(
                _contribution_from_child(child_id, child.feeder_circuit_id, child.plan)
            )

        request = _base_request(graph, boundary, tuple(contributions))
        plan = calculate_board_plan(request) if request is not None else None
        result = HierarchyBoardResult(
            board_id=board_id,
            parent_board_id=parent_by_id[board_id],
            feeder_circuit_id=boundary.feeder_circuit_id,
            status="CALCULATED" if plan is not None else "NO_DEMAND",
            plan=plan,
            child_board_ids=child_ids,
        )
        solved[board_id] = result
        visiting.remove(board_id)
        return result

    solve(roots[0])
    ordered_boards = tuple(solved[boundary.board_id] for boundary in boundaries)
    feeder_rollups = tuple(
        _feeder_rollup(board)
        for board in ordered_boards
        if board.parent_board_id is not None
    )
    return BoardHierarchyPlanResult(ordered_boards, feeder_rollups)
