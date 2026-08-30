"""Assess declared breaker constraints against calculated hierarchy demand.

This module intentionally performs a narrow capacity check only: whether a declared
breaker rating is at least the calculated design-current requirement at that graph
location. It does not claim protection compliance, selectivity, breaking-capacity,
fault-loop, thermal, or manufacturer coordination verification.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Literal

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph
from .catalogs import BREAKER_RATINGS_A
from .hierarchy_planner import BoardHierarchyPlanResult

ConstraintStatus = Literal["WITHIN_RATING", "RATING_EXCEEDED", "NO_DEMAND"]
ConstraintKind = Literal["INCOMER", "FINAL_CIRCUIT", "SUB_BOARD_FEEDER"]


@dataclass(frozen=True)
class BreakerRatingConstraint:
    node_id: str
    rating_a: float
    basis_note: str


@dataclass(frozen=True)
class BreakerConstraintAssessment:
    node_id: str
    kind: ConstraintKind
    circuit_id: str | None
    board_id: str
    declared_rating_a: float
    required_current_a: float
    status: ConstraintStatus
    margin_a: float
    basis_note: str
    limitation: str = (
        "Rating comparison only; protection compliance, selectivity, breaking capacity, "
        "fault-level duty and manufacturer coordination are not verified."
    )


def _validate_constraint(constraint: BreakerRatingConstraint) -> None:
    if not constraint.node_id.strip():
        raise ValueError("breaker constraint node_id is required")
    if not isfinite(constraint.rating_a) or constraint.rating_a <= 0:
        raise ValueError("breaker constraint rating must be finite and greater than 0")
    if constraint.rating_a not in tuple(float(value) for value in BREAKER_RATINGS_A):
        raise ValueError("breaker constraint rating must be one of the declared catalog ratings")
    if not constraint.basis_note.strip():
        raise ValueError("breaker constraint basis_note is required")


def _board_for_incomer(node: ElectricalNode) -> str:
    board_id = (node.board_ref or "").strip()
    if not board_id:
        raise ValueError(f"incomer {node.node_id} requires board_ref")
    return board_id


def _owning_board_id(graph: BoardElectricalGraph, node: ElectricalNode) -> str:
    for ancestor in graph.ancestors_of(node.node_id):
        if ancestor.kind == "busbar" and (ancestor.board_ref or "").strip():
            return (ancestor.board_ref or "").strip()
    raise ValueError(f"node {node.node_id} has no owning board busbar")


def _validate_hierarchy_identity(
    graph: BoardElectricalGraph,
    hierarchy: BoardHierarchyPlanResult,
) -> None:
    """Reject hierarchy results calculated from a different electrical topology.

    Board IDs alone are not a sufficient identity check: two graphs can use the same
    board names while containing different final circuits or sub-board feeders. Rating
    assessments must therefore confirm the circuit ownership and feeder relationships
    that provide the calculated current requirements before using those requirements.
    """
    hierarchy_board_ids = {board.board_id for board in hierarchy.boards}
    graph_board_ids = {
        graph.board_id.strip(),
        *(
            (node.board_ref or "").strip()
            for node in graph.nodes
            if node.kind == "sub_board"
        ),
    }
    if hierarchy_board_ids != graph_board_ids:
        raise ValueError("hierarchy result does not belong to this graph")

    graph_circuit_owner: dict[str, str] = {}
    for node in graph.nodes:
        if node.kind != "load":
            continue
        circuit_id = (node.circuit_id or "").strip()
        if not circuit_id:
            raise ValueError(f"load node {node.node_id} requires circuit_id")
        graph_circuit_owner[circuit_id] = _owning_board_id(graph, node)

    hierarchy_circuit_owner: dict[str, str] = {}
    for board_id, plan in hierarchy.plans_by_board_id.items():
        for circuit in plan.circuits:
            circuit_id = circuit.request.circuit_id.strip()
            if circuit_id in hierarchy_circuit_owner:
                raise ValueError(f"circuit {circuit_id} appears in multiple hierarchy board plans")
            hierarchy_circuit_owner[circuit_id] = board_id

    if hierarchy_circuit_owner != graph_circuit_owner:
        raise ValueError("hierarchy result final-circuit topology does not match this graph")

    graph_feeders: dict[str, tuple[str, str]] = {}
    for node in graph.nodes:
        if node.kind != "sub_board":
            continue
        feeder_id = (node.circuit_id or "").strip()
        child_board_id = (node.board_ref or "").strip()
        if not feeder_id:
            raise ValueError(f"sub_board node {node.node_id} requires circuit_id")
        if not child_board_id:
            raise ValueError(f"sub_board node {node.node_id} requires board_ref")
        graph_feeders[feeder_id] = (_owning_board_id(graph, node), child_board_id)

    hierarchy_feeders = {
        rollup.feeder_circuit_id: (rollup.parent_board_id, rollup.board_id)
        for rollup in hierarchy.feeder_rollups
    }
    if len(hierarchy_feeders) != len(hierarchy.feeder_rollups):
        raise ValueError("sub-board feeder circuit IDs must be unique")
    if hierarchy_feeders != graph_feeders:
        raise ValueError("hierarchy result sub-board feeder topology does not match this graph")


def _requirements(
    graph: BoardElectricalGraph,
    hierarchy: BoardHierarchyPlanResult,
) -> dict[str, tuple[ConstraintKind, str | None, str, float]]:
    plans = hierarchy.plans_by_board_id
    requirements: dict[str, tuple[ConstraintKind, str | None, str, float]] = {}

    # Every board incomer sees that board's full local + downstream phase demand.
    for node in graph.nodes:
        if node.kind != "incomer":
            continue
        board_id = _board_for_incomer(node)
        plan = plans.get(board_id)
        required = 0.0 if plan is None else plan.phase_balance.max_phase_current_a
        requirements[node.node_id] = ("INCOMER", None, board_id, required)

    # Final-circuit devices see the calculated branch design current.
    circuit_owner: dict[str, str] = {}
    circuit_required: dict[str, float] = {}
    for board_id, plan in plans.items():
        for circuit in plan.circuits:
            cid = circuit.request.circuit_id
            if cid in circuit_owner:
                raise ValueError(f"circuit {cid} appears in multiple hierarchy board plans")
            circuit_owner[cid] = board_id
            circuit_required[cid] = circuit.design_current_a

    feeder_by_id = {rollup.feeder_circuit_id: rollup for rollup in hierarchy.feeder_rollups}
    if len(feeder_by_id) != len(hierarchy.feeder_rollups):
        raise ValueError("sub-board feeder circuit IDs must be unique")

    for node in graph.nodes:
        if node.kind != "protective_device" or not node.circuit_id:
            continue
        cid = node.circuit_id
        if cid in circuit_required:
            requirements[node.node_id] = (
                "FINAL_CIRCUIT",
                cid,
                circuit_owner[cid],
                circuit_required[cid],
            )
            continue
        rollup = feeder_by_id.get(cid)
        if rollup is not None:
            requirements[node.node_id] = (
                "SUB_BOARD_FEEDER",
                cid,
                rollup.parent_board_id,
                rollup.required_current_a,
            )

    return requirements


def assess_breaker_constraints(
    graph: BoardElectricalGraph,
    hierarchy: BoardHierarchyPlanResult,
    constraints: tuple[BreakerRatingConstraint, ...],
) -> tuple[BreakerConstraintAssessment, ...]:
    """Compare declared ratings with calculated current requirements at graph nodes."""
    validate_board_graph(graph)
    _validate_hierarchy_identity(graph, hierarchy)

    by_node = graph.node_by_id
    seen: set[str] = set()
    for constraint in constraints:
        _validate_constraint(constraint)
        node_id = constraint.node_id.strip()
        if node_id in seen:
            raise ValueError(f"duplicate breaker constraint for node {node_id}")
        seen.add(node_id)
        node = by_node.get(node_id)
        if node is None:
            raise ValueError(f"breaker constraint references unknown node {node_id}")
        if node.kind not in ("incomer", "protective_device"):
            raise ValueError(
                f"breaker constraint node {node_id} must be an incomer or protective_device"
            )

    requirements = _requirements(graph, hierarchy)
    assessments: list[BreakerConstraintAssessment] = []
    for constraint in constraints:
        node_id = constraint.node_id.strip()
        requirement = requirements.get(node_id)
        if requirement is None:
            raise ValueError(
                f"breaker constraint node {node_id} has no calculated hierarchy current requirement"
            )
        kind, circuit_id, board_id, required = requirement
        margin = constraint.rating_a - required
        status: ConstraintStatus
        if required <= 0:
            status = "NO_DEMAND"
        elif margin >= 0:
            status = "WITHIN_RATING"
        else:
            status = "RATING_EXCEEDED"
        assessments.append(BreakerConstraintAssessment(
            node_id=node_id,
            kind=kind,
            circuit_id=circuit_id,
            board_id=board_id,
            declared_rating_a=constraint.rating_a,
            required_current_a=required,
            status=status,
            margin_a=margin,
            basis_note=constraint.basis_note.strip(),
        ))
    return tuple(assessments)
