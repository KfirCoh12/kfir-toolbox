"""Per-board calculation boundaries over the shared electrical hierarchy.

This module identifies each board in a hierarchy and translates only that board's
own final-load circuits into the existing BoardPlanRequest model. Callers may supply
exact CircuitDesignRequest overrides for graph loads whose engineering basis is not
representable by the legacy kW-only graph fields (for example fixed-current/manual
or kVA requirements). Downstream board demand is still handled separately by the
hierarchy planner; no feeder diversity or selectivity is invented here.
"""
from dataclasses import dataclass, replace
from typing import Literal

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph
from .board_planner import BoardPhasePreference, BoardPlanRequest, BoardPlanResult
from .circuit_engine import CircuitDesignRequest

BoundaryStatus = Literal["READY", "NO_FINAL_LOADS"]


@dataclass(frozen=True)
class BoardCalculationBoundary:
    board_id: str
    description: str
    anchor_node_id: str
    busbar_node_id: str
    feeder_circuit_id: str | None
    final_load_node_ids: tuple[str, ...]
    status: BoundaryStatus
    request: BoardPlanRequest | None


def _board_busbars(graph: BoardElectricalGraph) -> tuple[ElectricalNode, ...]:
    return tuple(
        node
        for node in graph.nodes
        if node.kind == "busbar" and node.board_ref is not None
    )


def _owning_busbar(graph: BoardElectricalGraph, node: ElectricalNode) -> ElectricalNode:
    for ancestor in graph.ancestors_of(node.node_id):
        if ancestor.kind == "busbar" and ancestor.board_ref is not None:
            return ancestor
    raise ValueError(f"node {node.node_id} is not downstream of a board busbar")


def _board_metadata(
    graph: BoardElectricalGraph, busbar: ElectricalNode
) -> tuple[str, str, str, str | None]:
    board_id = (busbar.board_ref or "").strip()
    if not board_id:
        raise ValueError(f"busbar {busbar.node_id} requires board_ref")

    if board_id == graph.board_id.strip():
        return board_id, graph.description.strip(), graph.root_nodes[0].node_id, None

    for ancestor in graph.ancestors_of(busbar.node_id):
        if ancestor.kind == "sub_board" and ancestor.board_ref == board_id:
            return (
                board_id,
                ancestor.label.strip(),
                ancestor.node_id,
                ancestor.circuit_id,
            )
    raise ValueError(f"board {board_id} has no matching sub_board anchor")


def _validate_override(
    graph: BoardElectricalGraph,
    node: ElectricalNode,
    request: CircuitDesignRequest,
) -> CircuitDesignRequest:
    cid = (node.circuit_id or "").strip()
    if request.circuit_id.strip() != cid:
        raise ValueError(f"circuit override for {cid} must keep the graph circuit_id")
    if request.phase not in ("single", "three"):
        raise ValueError(f"{cid}: override phase must be single or three")
    expected_voltage = (
        graph.line_to_line_voltage_v
        if request.phase == "three"
        else graph.line_to_neutral_voltage_v
    )
    if request.voltage_v != expected_voltage:
        voltage_kind = "line-to-line" if request.phase == "three" else "line-to-neutral"
        raise ValueError(
            f"{cid}: override voltage {request.voltage_v:g} V does not match board "
            f"{voltage_kind} voltage {expected_voltage:g} V"
        )
    if request.phase == "three" and node.phase_preference != "Auto":
        raise ValueError(f"{cid}: phase preference only applies to single-phase circuits")
    return request


def _legacy_kw_request(
    graph: BoardElectricalGraph,
    node: ElectricalNode,
) -> CircuitDesignRequest:
    cid = (node.circuit_id or "").strip()
    if node.load_kw is None or node.load_kw <= 0:
        raise ValueError(
            f"{cid}: graph load has no positive kW value; provide an exact circuit request override"
        )
    if node.phase not in ("single", "three"):
        raise ValueError(f"{cid}: phase must be single or three")
    if node.power_factor is None or not 0 < node.power_factor <= 1:
        raise ValueError(f"{cid}: power_factor must be greater than 0 and at most 1")
    if node.demand_factor is None or not 0 < node.demand_factor <= 1:
        raise ValueError(f"{cid}: demand_factor must be greater than 0 and at most 1")
    if node.material not in ("copper", "aluminium"):
        raise ValueError(f"{cid}: material must be copper or aluminium")
    if node.phase == "three" and node.phase_preference != "Auto":
        raise ValueError(f"{cid}: phase preference only applies to single-phase circuits")

    return CircuitDesignRequest(
        circuit_id=cid,
        description=node.label.strip(),
        load_type="kw",
        load_value=node.load_kw,
        voltage_v=(
            graph.line_to_line_voltage_v
            if node.phase == "three"
            else graph.line_to_neutral_voltage_v
        ),
        phase=node.phase,
        power_factor=node.power_factor,
        demand_factor=node.demand_factor,
        material=node.material,
    )


def _request_for_loads(
    graph: BoardElectricalGraph,
    *,
    board_id: str,
    description: str,
    loads: tuple[ElectricalNode, ...],
    overrides_by_id: dict[str, CircuitDesignRequest],
) -> BoardPlanRequest:
    circuits: list[CircuitDesignRequest] = []
    preferences: list[BoardPhasePreference] = []

    for node in loads:
        cid = (node.circuit_id or "").strip()
        if not cid:
            raise ValueError(f"load node {node.node_id} requires circuit_id")
        request = overrides_by_id.get(cid)
        if request is None:
            request = _legacy_kw_request(graph, node)
        else:
            request = _validate_override(graph, node, request)
        circuits.append(request)

        if request.phase == "single" and node.phase_preference in ("L1", "L2", "L3"):
            preferences.append(BoardPhasePreference(cid, node.phase_preference))

    return BoardPlanRequest(
        board_id=board_id,
        description=description,
        circuits=tuple(circuits),
        line_to_line_voltage_v=graph.line_to_line_voltage_v,
        line_to_neutral_voltage_v=graph.line_to_neutral_voltage_v,
        phase_preferences=tuple(preferences),
    )


def calculation_boundaries_from_graph(
    graph: BoardElectricalGraph,
    circuit_request_overrides: tuple[CircuitDesignRequest, ...] = tuple(),
) -> tuple[BoardCalculationBoundary, ...]:
    """Return one explicit calculation boundary for every board in the hierarchy.

    Exact request overrides are keyed by circuit_id and replace only the load basis for
    that final circuit. This lets manual/fixed-A and kVA circuits retain their real
    engineering basis without converting them into fictitious kW values.
    """
    validate_board_graph(graph)
    overrides_by_id: dict[str, CircuitDesignRequest] = {}
    for request in circuit_request_overrides:
        cid = request.circuit_id.strip()
        if not cid:
            raise ValueError("circuit request override circuit_id is required")
        if cid in overrides_by_id:
            raise ValueError(f"duplicate circuit request override for {cid}")
        overrides_by_id[cid] = request

    loads = tuple(node for node in graph.nodes if node.kind == "load")
    graph_load_ids = {(node.circuit_id or "").strip() for node in loads}
    unknown_overrides = tuple(cid for cid in overrides_by_id if cid not in graph_load_ids)
    if unknown_overrides:
        raise ValueError(
            "circuit request override references unknown graph load: "
            + ", ".join(unknown_overrides)
        )

    owner_by_load = {
        node.node_id: _owning_busbar(graph, node).node_id for node in loads
    }

    boundaries: list[BoardCalculationBoundary] = []
    seen_board_ids: set[str] = set()
    for busbar in _board_busbars(graph):
        board_id, description, anchor_node_id, feeder_circuit_id = _board_metadata(
            graph, busbar
        )
        if board_id in seen_board_ids:
            raise ValueError(f"board {board_id} has multiple busbars in hierarchy")
        seen_board_ids.add(board_id)

        owned_loads = tuple(
            node for node in loads if owner_by_load[node.node_id] == busbar.node_id
        )
        request = (
            _request_for_loads(
                graph,
                board_id=board_id,
                description=description,
                loads=owned_loads,
                overrides_by_id=overrides_by_id,
            )
            if owned_loads
            else None
        )
        boundaries.append(
            BoardCalculationBoundary(
                board_id=board_id,
                description=description,
                anchor_node_id=anchor_node_id,
                busbar_node_id=busbar.node_id,
                feeder_circuit_id=feeder_circuit_id,
                final_load_node_ids=tuple(node.node_id for node in owned_loads),
                status="READY" if request is not None else "NO_FINAL_LOADS",
                request=request,
            )
        )

    return tuple(boundaries)


def enrich_graph_with_board_plans(
    graph: BoardElectricalGraph,
    plans: tuple[BoardPlanResult, ...],
    circuit_request_overrides: tuple[CircuitDesignRequest, ...] = tuple(),
) -> BoardElectricalGraph:
    """Apply independently calculated board results back to their owned branches."""
    boundaries = calculation_boundaries_from_graph(graph, circuit_request_overrides)
    boundary_by_id = {boundary.board_id: boundary for boundary in boundaries}
    plan_by_id: dict[str, BoardPlanResult] = {}

    for plan in plans:
        board_id = plan.request.board_id.strip()
        if board_id in plan_by_id:
            raise ValueError(f"duplicate board plan for {board_id}")
        boundary = boundary_by_id.get(board_id)
        if boundary is None:
            raise ValueError(f"board plan {board_id} does not belong to this hierarchy")
        if boundary.request is None:
            raise ValueError(f"board {board_id} has no final loads to calculate")
        expected = tuple(c.circuit_id for c in boundary.request.circuits)
        actual = tuple(c.circuit_id for c in plan.request.circuits)
        if actual != expected:
            raise ValueError(
                f"board plan {board_id} circuits do not match hierarchy boundary"
            )
        plan_by_id[board_id] = plan

    circuit_owner: dict[str, str] = {}
    for boundary in boundaries:
        for load_node_id in boundary.final_load_node_ids:
            load = graph.node_by_id[load_node_id]
            if load.circuit_id is not None:
                circuit_owner[load.circuit_id] = boundary.board_id

    rows_by_board = {
        board_id: {row.circuit_id: row for row in plan.schedule_rows}
        for board_id, plan in plan_by_id.items()
    }
    enriched: list[ElectricalNode] = []
    for node in graph.nodes:
        cid = node.circuit_id
        owner = circuit_owner.get(cid) if cid else None
        row = rows_by_board.get(owner, {}).get(cid) if owner else None
        if row is None:
            enriched.append(node)
            continue

        common = dict(
            assigned_phase=row.assigned_phase,
            scope_status=row.scope_status,
            issue_codes=row.blocking_issue_codes,
        )
        if node.kind == "protective_device":
            enriched.append(replace(node, rating_a=row.breaker_a, **common))
        elif node.kind == "cable":
            enriched.append(
                replace(
                    node,
                    cable_mm2=row.cable_mm2,
                    cable_runs=row.cable_runs,
                    **common,
                )
            )
        elif node.kind == "load":
            enriched.append(replace(node, **common))
        else:
            enriched.append(node)

    updated = replace(graph, nodes=tuple(enriched))
    validate_board_graph(updated)
    return updated
