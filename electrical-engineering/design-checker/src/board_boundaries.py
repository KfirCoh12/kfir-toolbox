"""Per-board calculation boundaries over the shared electrical hierarchy.

This module identifies each board in a hierarchy and translates only that board's
own final-load circuits into the existing BoardPlanRequest model. It deliberately
does not aggregate downstream board demand into feeder circuits: feeder sizing,
diversity, and selectivity remain outside the implemented scope.
"""
from dataclasses import dataclass
from typing import Literal

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph
from .board_planner import BoardPhasePreference, BoardPlanRequest
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


def _request_for_loads(
    graph: BoardElectricalGraph,
    *,
    board_id: str,
    description: str,
    loads: tuple[ElectricalNode, ...],
) -> BoardPlanRequest:
    circuits: list[CircuitDesignRequest] = []
    preferences: list[BoardPhasePreference] = []

    for node in loads:
        cid = (node.circuit_id or "").strip()
        if not cid:
            raise ValueError(f"load node {node.node_id} requires circuit_id")
        if node.load_kw is None or node.load_kw <= 0:
            raise ValueError(f"{cid}: load_kw must be greater than 0")
        if node.phase not in ("single", "three"):
            raise ValueError(f"{cid}: phase must be single or three")
        if node.power_factor is None or not 0 < node.power_factor <= 1:
            raise ValueError(f"{cid}: power_factor must be greater than 0 and at most 1")
        if node.demand_factor is None or not 0 < node.demand_factor <= 1:
            raise ValueError(f"{cid}: demand_factor must be greater than 0 and at most 1")
        if node.material not in ("copper", "aluminium"):
            raise ValueError(f"{cid}: material must be copper or aluminium")
        if node.phase == "three" and node.phase_preference != "Auto":
            raise ValueError(
                f"{cid}: phase preference only applies to single-phase circuits"
            )

        circuits.append(
            CircuitDesignRequest(
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
        )
        if node.phase == "single" and node.phase_preference in ("L1", "L2", "L3"):
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
) -> tuple[BoardCalculationBoundary, ...]:
    """Return one explicit calculation boundary for every board in the hierarchy.

    A boundary is READY only when the board directly owns at least one final load.
    Downstream boards are never flattened into an upstream request, and sub-board
    feeders are not synthesized as loads. Empty boards remain visible as
    NO_FINAL_LOADS boundaries so callers can distinguish "nothing to calculate" from
    a missing board.
    """
    validate_board_graph(graph)
    loads = tuple(node for node in graph.nodes if node.kind == "load")
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
