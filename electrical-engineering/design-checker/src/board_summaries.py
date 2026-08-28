"""Renderer-neutral summaries for board calculation boundaries.

A summary exposes local board results without propagating them into upstream feeders.
This intentionally keeps feeder demand, feeder sizing, diversity, selectivity, and
protection verification unresolved until those engineering contracts are implemented.
"""
from dataclasses import dataclass
from typing import Literal

from .board_boundaries import BoardCalculationBoundary, calculation_boundaries_from_graph
from .board_graph import BoardElectricalGraph
from .board_planner import BoardPlanResult, BoardScopeStatus

BoardSummaryStatus = Literal["NO_FINAL_LOADS", "UNCALCULATED", "CALCULATED"]
FeederDemandStatus = Literal["ROOT_BOARD", "NOT_EVALUATED"]


@dataclass(frozen=True)
class BoardHierarchySummary:
    board_id: str
    description: str
    anchor_node_id: str
    busbar_node_id: str
    feeder_circuit_id: str | None
    final_load_count: int
    status: BoardSummaryStatus
    local_scope_status: BoardScopeStatus | None
    l1_current_a: float | None
    l2_current_a: float | None
    l3_current_a: float | None
    phase_spread_a: float | None
    local_incomer_candidate_a: float | None
    local_incomer_required_current_a: float | None
    feeder_demand_status: FeederDemandStatus

    @property
    def has_local_calculation(self) -> bool:
        return self.status == "CALCULATED"


def _validate_plan_for_boundary(
    boundary: BoardCalculationBoundary, plan: BoardPlanResult
) -> None:
    board_id = plan.request.board_id.strip()
    if board_id != boundary.board_id:
        raise ValueError(
            f"board plan {board_id} does not match hierarchy boundary {boundary.board_id}"
        )
    if boundary.request is None:
        raise ValueError(f"board {boundary.board_id} has no final loads to calculate")

    expected = tuple(c.circuit_id for c in boundary.request.circuits)
    actual = tuple(c.circuit_id for c in plan.request.circuits)
    if actual != expected:
        raise ValueError(
            f"board plan {boundary.board_id} circuits do not match hierarchy boundary"
        )


def _summary_without_plan(boundary: BoardCalculationBoundary) -> BoardHierarchySummary:
    status: BoardSummaryStatus = (
        "NO_FINAL_LOADS" if boundary.status == "NO_FINAL_LOADS" else "UNCALCULATED"
    )
    return BoardHierarchySummary(
        board_id=boundary.board_id,
        description=boundary.description,
        anchor_node_id=boundary.anchor_node_id,
        busbar_node_id=boundary.busbar_node_id,
        feeder_circuit_id=boundary.feeder_circuit_id,
        final_load_count=len(boundary.final_load_node_ids),
        status=status,
        local_scope_status=None,
        l1_current_a=None,
        l2_current_a=None,
        l3_current_a=None,
        phase_spread_a=None,
        local_incomer_candidate_a=None,
        local_incomer_required_current_a=None,
        feeder_demand_status=(
            "ROOT_BOARD" if boundary.feeder_circuit_id is None else "NOT_EVALUATED"
        ),
    )


def _summary_with_plan(
    boundary: BoardCalculationBoundary, plan: BoardPlanResult
) -> BoardHierarchySummary:
    _validate_plan_for_boundary(boundary, plan)
    balance = plan.phase_balance
    incomer = plan.incomer_candidate
    return BoardHierarchySummary(
        board_id=boundary.board_id,
        description=boundary.description,
        anchor_node_id=boundary.anchor_node_id,
        busbar_node_id=boundary.busbar_node_id,
        feeder_circuit_id=boundary.feeder_circuit_id,
        final_load_count=len(boundary.final_load_node_ids),
        status="CALCULATED",
        local_scope_status=plan.scope_status,
        l1_current_a=balance.l1_current_a,
        l2_current_a=balance.l2_current_a,
        l3_current_a=balance.l3_current_a,
        phase_spread_a=balance.spread_a,
        local_incomer_candidate_a=incomer.breaker_rating_a,
        local_incomer_required_current_a=incomer.required_current_a,
        feeder_demand_status=(
            "ROOT_BOARD" if boundary.feeder_circuit_id is None else "NOT_EVALUATED"
        ),
    )


def board_hierarchy_summaries(
    graph: BoardElectricalGraph,
    plans: tuple[BoardPlanResult, ...] = tuple(),
) -> tuple[BoardHierarchySummary, ...]:
    """Summarize every board while preserving the feeder-demand boundary.

    Local board phase currents and the existing provisional local incomer candidate
    may be exposed when a matching plan is supplied. These values are never copied to
    the upstream feeder. A downstream board always reports feeder demand as
    NOT_EVALUATED until an explicit aggregation model exists.
    """
    boundaries = calculation_boundaries_from_graph(graph)
    boundary_by_id = {boundary.board_id: boundary for boundary in boundaries}
    plans_by_id: dict[str, BoardPlanResult] = {}

    for plan in plans:
        board_id = plan.request.board_id.strip()
        if board_id in plans_by_id:
            raise ValueError(f"duplicate board plan for {board_id}")
        boundary = boundary_by_id.get(board_id)
        if boundary is None:
            raise ValueError(f"board plan {board_id} does not belong to this hierarchy")
        _validate_plan_for_boundary(boundary, plan)
        plans_by_id[board_id] = plan

    return tuple(
        _summary_with_plan(boundary, plans_by_id[boundary.board_id])
        if boundary.board_id in plans_by_id
        else _summary_without_plan(boundary)
        for boundary in boundaries
    )
