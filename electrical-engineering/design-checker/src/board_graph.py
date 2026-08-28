"""Hierarchy-native electrical board model for planning and single-line views.

The graph is the shared design model. A schedule, calculation request, and SLD are
views of the same parent/child electrical structure rather than separate sources of
truth. V0 supports the ordinary radial board hierarchy while deliberately keeping
node/parent relationships generic enough for sub-boards and richer topologies later.
"""
from dataclasses import dataclass, replace
from math import isfinite
from typing import Literal

from .board_planner import BoardPhasePreference, BoardPlanRequest, BoardPlanResult
from .circuit_engine import CircuitDesignRequest

ElectricalNodeKind = Literal[
    "source",
    "incomer",
    "busbar",
    "protective_device",
    "cable",
    "load",
    "sub_board",
]
CircuitPhase = Literal["single", "three"]
CircuitMaterial = Literal["copper", "aluminium"]
PhasePreference = Literal["Auto", "L1", "L2", "L3"]
ScopeStatus = Literal["SUPPORTED_SCOPE", "PARTIAL_SCOPE", "NOT_VERIFIED"]


@dataclass(frozen=True)
class ElectricalNode:
    node_id: str
    kind: ElectricalNodeKind
    label: str
    parent_id: str | None
    circuit_id: str | None = None

    # Load/circuit design inputs. These live on the load node in the current model.
    load_kw: float | None = None
    phase: CircuitPhase | None = None
    power_factor: float | None = None
    demand_factor: float | None = None
    material: CircuitMaterial | None = None
    phase_preference: PhasePreference = "Auto"

    # Calculated/enriched values used by schedule and SLD views.
    rating_a: float | None = None
    cable_mm2: float | None = None
    cable_runs: int | None = None
    assigned_phase: str | None = None
    scope_status: ScopeStatus | None = None
    issue_codes: tuple[str, ...] = tuple()


@dataclass(frozen=True)
class BoardElectricalGraph:
    board_id: str
    description: str
    line_to_line_voltage_v: float
    line_to_neutral_voltage_v: float
    nodes: tuple[ElectricalNode, ...]

    @property
    def node_by_id(self) -> dict[str, ElectricalNode]:
        return {node.node_id: node for node in self.nodes}

    @property
    def root_nodes(self) -> tuple[ElectricalNode, ...]:
        return tuple(node for node in self.nodes if node.parent_id is None)

    def children_of(self, node_id: str) -> tuple[ElectricalNode, ...]:
        return tuple(node for node in self.nodes if node.parent_id == node_id)

    def ancestors_of(self, node_id: str) -> tuple[ElectricalNode, ...]:
        by_id = self.node_by_id
        if node_id not in by_id:
            raise ValueError(f"unknown node {node_id}")
        ancestors: list[ElectricalNode] = []
        current = by_id[node_id]
        seen = {node_id}
        while current.parent_id is not None:
            if current.parent_id in seen:
                raise ValueError("board hierarchy contains a cycle")
            parent = by_id.get(current.parent_id)
            if parent is None:
                raise ValueError(f"node {current.node_id} references missing parent {current.parent_id}")
            ancestors.append(parent)
            seen.add(parent.node_id)
            current = parent
        return tuple(ancestors)


def validate_board_graph(graph: BoardElectricalGraph) -> None:
    if not graph.board_id.strip():
        raise ValueError("board_id is required")
    if not graph.description.strip():
        raise ValueError("description is required")
    for name, value in (
        ("line_to_line_voltage_v", graph.line_to_line_voltage_v),
        ("line_to_neutral_voltage_v", graph.line_to_neutral_voltage_v),
    ):
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a finite value greater than 0")

    ids = [node.node_id.strip() for node in graph.nodes]
    if any(not node_id for node_id in ids):
        raise ValueError("node_id is required")
    if len(ids) != len(set(ids)):
        raise ValueError("node_id values must be unique within a board")
    if any(not node.label.strip() for node in graph.nodes):
        raise ValueError("every electrical node requires a label")

    by_id = graph.node_by_id
    for node in graph.nodes:
        if node.parent_id is not None and node.parent_id not in by_id:
            raise ValueError(f"node {node.node_id} references missing parent {node.parent_id}")
        graph.ancestors_of(node.node_id)

    if len(graph.root_nodes) != 1:
        raise ValueError("board hierarchy must contain exactly one root node")
    if graph.root_nodes[0].kind != "source":
        raise ValueError("board hierarchy root must be a source")

    load_circuit_ids = [
        node.circuit_id.strip()
        for node in graph.nodes
        if node.kind == "load" and node.circuit_id is not None
    ]
    if len(load_circuit_ids) != len(set(load_circuit_ids)):
        raise ValueError("load circuit_id values must be unique within a board")


def make_radial_board_graph(
    *,
    board_id: str,
    description: str,
    line_to_line_voltage_v: float = 400.0,
    line_to_neutral_voltage_v: float = 230.0,
) -> BoardElectricalGraph:
    """Create the minimal live board hierarchy: source -> incomer -> busbar."""
    graph = BoardElectricalGraph(
        board_id=board_id,
        description=description,
        line_to_line_voltage_v=line_to_line_voltage_v,
        line_to_neutral_voltage_v=line_to_neutral_voltage_v,
        nodes=(
            ElectricalNode("source", "source", "Supply", None),
            ElectricalNode("incomer", "incomer", "Main incomer", "source"),
            ElectricalNode("busbar", "busbar", "Main busbar", "incomer"),
        ),
    )
    validate_board_graph(graph)
    return graph


def add_radial_circuit(
    graph: BoardElectricalGraph,
    *,
    circuit_id: str,
    description: str,
    load_kw: float = 1.0,
    phase: CircuitPhase = "single",
    power_factor: float = 0.9,
    demand_factor: float = 1.0,
    material: CircuitMaterial = "copper",
    phase_preference: PhasePreference = "Auto",
    parent_busbar_id: str = "busbar",
) -> BoardElectricalGraph:
    """Add protection -> cable -> load beneath a busbar as one radial circuit branch."""
    cid = circuit_id.strip()
    if not cid:
        raise ValueError("circuit_id is required")
    if parent_busbar_id not in graph.node_by_id:
        raise ValueError(f"unknown parent busbar {parent_busbar_id}")
    if graph.node_by_id[parent_busbar_id].kind != "busbar":
        raise ValueError("radial circuit parent must be a busbar")
    if any(node.circuit_id == cid for node in graph.nodes if node.circuit_id is not None):
        raise ValueError(f"circuit_id {cid} already exists")

    device_id = f"{cid}:device"
    cable_id = f"{cid}:cable"
    load_id = f"{cid}:load"
    additions = (
        ElectricalNode(device_id, "protective_device", f"{cid} protection", parent_busbar_id, circuit_id=cid),
        ElectricalNode(cable_id, "cable", f"{cid} cable", device_id, circuit_id=cid),
        ElectricalNode(
            load_id,
            "load",
            description,
            cable_id,
            circuit_id=cid,
            load_kw=load_kw,
            phase=phase,
            power_factor=power_factor,
            demand_factor=demand_factor,
            material=material,
            phase_preference=phase_preference,
        ),
    )
    updated = replace(graph, nodes=graph.nodes + additions)
    validate_board_graph(updated)
    return updated


def remove_circuit(graph: BoardElectricalGraph, circuit_id: str) -> BoardElectricalGraph:
    cid = circuit_id.strip()
    updated = replace(
        graph,
        nodes=tuple(node for node in graph.nodes if node.circuit_id != cid),
    )
    validate_board_graph(updated)
    return updated


def board_plan_request_from_graph(graph: BoardElectricalGraph) -> BoardPlanRequest:
    """Translate complete load nodes into the existing shared board calculation engine."""
    validate_board_graph(graph)
    circuits: list[CircuitDesignRequest] = []
    preferences: list[BoardPhasePreference] = []
    for node in graph.nodes:
        if node.kind != "load":
            continue
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
            raise ValueError(f"{cid}: phase preference only applies to single-phase circuits")

        circuits.append(CircuitDesignRequest(
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
        ))
        if node.phase == "single" and node.phase_preference in ("L1", "L2", "L3"):
            preferences.append(BoardPhasePreference(cid, node.phase_preference))

    if not circuits:
        raise ValueError("at least one load circuit is required")
    return BoardPlanRequest(
        board_id=graph.board_id,
        description=graph.description,
        circuits=tuple(circuits),
        line_to_line_voltage_v=graph.line_to_line_voltage_v,
        line_to_neutral_voltage_v=graph.line_to_neutral_voltage_v,
        phase_preferences=tuple(preferences),
    )


def enrich_graph_with_plan(
    graph: BoardElectricalGraph,
    plan: BoardPlanResult,
) -> BoardElectricalGraph:
    """Attach calculated branch values to their existing electrical nodes."""
    if plan.request.board_id.strip() != graph.board_id.strip():
        raise ValueError("board plan does not belong to this graph")
    rows = {row.circuit_id: row for row in plan.schedule_rows}
    enriched: list[ElectricalNode] = []
    for node in graph.nodes:
        cid = node.circuit_id
        row = rows.get(cid) if cid else None
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
            enriched.append(replace(
                node,
                cable_mm2=row.cable_mm2,
                cable_runs=row.cable_runs,
                **common,
            ))
        elif node.kind == "load":
            enriched.append(replace(node, **common))
        else:
            enriched.append(node)
    updated = replace(graph, nodes=tuple(enriched))
    validate_board_graph(updated)
    return updated
