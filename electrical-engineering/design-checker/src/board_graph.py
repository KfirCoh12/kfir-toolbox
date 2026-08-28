"""Hierarchy-native electrical board model for planning and single-line views.

The graph is the shared design model. A schedule, calculation request, and SLD are
views of the same parent/child electrical structure rather than separate sources of
truth. The model supports radial final circuits, lightweight downstream fields, and
full downstream sub-board feeders while keeping calculation logic delegated to the
existing circuit/board engines.
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
    "field",
    "sub_board",
]
CircuitPhase = Literal["single", "three"]
CircuitMaterial = Literal["copper", "aluminium"]
PhasePreference = Literal["Auto", "L1", "L2", "L3"]
ScopeStatus = Literal["SUPPORTED_SCOPE", "PARTIAL_SCOPE", "NOT_VERIFIED"]

_ALLOWED_CHILD_KINDS: dict[ElectricalNodeKind, tuple[ElectricalNodeKind, ...]] = {
    "source": ("incomer",),
    "incomer": ("busbar",),
    "busbar": ("protective_device",),
    "protective_device": ("cable",),
    "cable": ("load", "field", "sub_board"),
    "load": tuple(),
    "field": ("busbar",),
    "sub_board": ("incomer",),
}


@dataclass(frozen=True)
class ElectricalNode:
    node_id: str
    kind: ElectricalNodeKind
    label: str
    parent_id: str | None
    circuit_id: str | None = None
    board_ref: str | None = None
    field_ref: str | None = None
    load_kw: float | None = None
    phase: CircuitPhase | None = None
    power_factor: float | None = None
    demand_factor: float | None = None
    material: CircuitMaterial | None = None
    phase_preference: PhasePreference = "Auto"
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
                raise ValueError(
                    f"node {current.node_id} references missing parent {current.parent_id}"
                )
            ancestors.append(parent)
            seen.add(parent.node_id)
            current = parent
        return tuple(ancestors)

    def descendants_of(self, node_id: str) -> tuple[ElectricalNode, ...]:
        if node_id not in self.node_by_id:
            raise ValueError(f"unknown node {node_id}")
        descendants: list[ElectricalNode] = []
        pending = list(self.children_of(node_id))
        while pending:
            node = pending.pop(0)
            descendants.append(node)
            pending[0:0] = list(self.children_of(node.node_id))
        return tuple(descendants)


def _validate_parent_child(parent: ElectricalNode, child: ElectricalNode) -> None:
    if child.kind not in _ALLOWED_CHILD_KINDS[parent.kind]:
        raise ValueError(
            f"invalid electrical hierarchy: {parent.kind} cannot directly feed {child.kind}"
        )


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
        if node.parent_id is not None:
            parent = by_id.get(node.parent_id)
            if parent is None:
                raise ValueError(
                    f"node {node.node_id} references missing parent {node.parent_id}"
                )
            _validate_parent_child(parent, node)
        graph.ancestors_of(node.node_id)

    if len(graph.root_nodes) != 1:
        raise ValueError("board hierarchy must contain exactly one root node")
    if graph.root_nodes[0].kind != "source":
        raise ValueError("board hierarchy root must be a source")

    for node in graph.nodes:
        children = graph.children_of(node.node_id)
        if node.kind in ("source", "sub_board"):
            incomers = tuple(child for child in children if child.kind == "incomer")
            if len(incomers) != 1:
                raise ValueError(
                    f"{node.kind} {node.node_id} must have exactly one incomer"
                )
        if node.kind in ("incomer", "field"):
            busbars = tuple(child for child in children if child.kind == "busbar")
            if len(busbars) != 1:
                raise ValueError(
                    f"{node.kind} {node.node_id} must have exactly one busbar"
                )
        if node.kind == "cable":
            endpoints = tuple(
                child
                for child in children
                if child.kind in ("load", "field", "sub_board")
            )
            if len(endpoints) != 1:
                raise ValueError(
                    f"cable {node.node_id} must terminate at exactly one load, field or sub_board"
                )

    load_circuit_ids = [
        node.circuit_id.strip()
        for node in graph.nodes
        if node.kind == "load" and node.circuit_id is not None
    ]
    if len(load_circuit_ids) != len(set(load_circuit_ids)):
        raise ValueError("load circuit_id values must be unique within a board")

    field_refs = [
        node.field_ref.strip()
        for node in graph.nodes
        if node.kind == "field" and node.field_ref is not None
    ]
    if any(not ref for ref in field_refs):
        raise ValueError("field field_ref is required")
    if len(field_refs) != len(set(field_refs)):
        raise ValueError("field_ref values must be unique within a hierarchy")

    sub_board_refs = [
        node.board_ref.strip()
        for node in graph.nodes
        if node.kind == "sub_board" and node.board_ref is not None
    ]
    if any(not ref for ref in sub_board_refs):
        raise ValueError("sub_board board_ref is required")
    if len(sub_board_refs) != len(set(sub_board_refs)):
        raise ValueError("sub_board board_ref values must be unique within a hierarchy")
    if graph.board_id.strip() in sub_board_refs:
        raise ValueError("sub_board board_ref cannot equal the root board_id")


def make_radial_board_graph(
    *,
    board_id: str,
    description: str,
    line_to_line_voltage_v: float = 400.0,
    line_to_neutral_voltage_v: float = 230.0,
) -> BoardElectricalGraph:
    graph = BoardElectricalGraph(
        board_id=board_id,
        description=description,
        line_to_line_voltage_v=line_to_line_voltage_v,
        line_to_neutral_voltage_v=line_to_neutral_voltage_v,
        nodes=(
            ElectricalNode(
                "source", "source", "Supply", None, board_ref=board_id.strip()
            ),
            ElectricalNode(
                "incomer",
                "incomer",
                "Main incomer",
                "source",
                board_ref=board_id.strip(),
            ),
            ElectricalNode(
                "busbar",
                "busbar",
                "Main busbar",
                "incomer",
                board_ref=board_id.strip(),
            ),
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
    cid = circuit_id.strip()
    if not cid:
        raise ValueError("circuit_id is required")
    if parent_busbar_id not in graph.node_by_id:
        raise ValueError(f"unknown parent busbar {parent_busbar_id}")
    if graph.node_by_id[parent_busbar_id].kind != "busbar":
        raise ValueError("radial circuit parent must be a busbar")
    if any(
        node.circuit_id == cid for node in graph.nodes if node.circuit_id is not None
    ):
        raise ValueError(f"circuit_id {cid} already exists")

    device_id = f"{cid}:device"
    cable_id = f"{cid}:cable"
    load_id = f"{cid}:load"
    additions = (
        ElectricalNode(
            device_id,
            "protective_device",
            f"{cid} protection",
            parent_busbar_id,
            circuit_id=cid,
        ),
        ElectricalNode(
            cable_id, "cable", f"{cid} cable", device_id, circuit_id=cid
        ),
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


def add_field_feeder(
    graph: BoardElectricalGraph,
    *,
    feeder_id: str,
    field_id: str,
    description: str,
    parent_busbar_id: str = "busbar",
) -> BoardElectricalGraph:
    """Add busbar -> feeder protection -> cable -> field -> field busbar.

    A field is a lightweight downstream distribution group inside the same board
    planning boundary. Child final circuits remain part of the root board calculation.
    The field feeder itself is not yet auto-sized from downstream aggregate demand.
    """
    fid = feeder_id.strip()
    child_field_id = field_id.strip()
    child_description = description.strip()
    if not fid:
        raise ValueError("feeder_id is required")
    if not child_field_id:
        raise ValueError("field_id is required")
    if not child_description:
        raise ValueError("field description is required")
    if parent_busbar_id not in graph.node_by_id:
        raise ValueError(f"unknown parent busbar {parent_busbar_id}")
    if graph.node_by_id[parent_busbar_id].kind != "busbar":
        raise ValueError("field feeder parent must be a busbar")
    if any(
        node.circuit_id == fid for node in graph.nodes if node.circuit_id is not None
    ):
        raise ValueError(f"circuit_id {fid} already exists")
    if any(
        node.kind == "field" and node.field_ref == child_field_id
        for node in graph.nodes
    ):
        raise ValueError(f"field_id {child_field_id} already exists in hierarchy")

    prefix = f"{fid}:{child_field_id}"
    additions = (
        ElectricalNode(
            f"{fid}:device",
            "protective_device",
            f"{fid} field protection",
            parent_busbar_id,
            circuit_id=fid,
        ),
        ElectricalNode(
            f"{fid}:cable",
            "cable",
            f"{fid} field feeder cable",
            f"{fid}:device",
            circuit_id=fid,
        ),
        ElectricalNode(
            f"{prefix}:field",
            "field",
            child_description,
            f"{fid}:cable",
            circuit_id=fid,
            field_ref=child_field_id,
        ),
        ElectricalNode(
            f"{prefix}:busbar",
            "busbar",
            f"{child_field_id} busbar",
            f"{prefix}:field",
            field_ref=child_field_id,
        ),
    )
    updated = replace(graph, nodes=graph.nodes + additions)
    validate_board_graph(updated)
    return updated


def add_sub_board_feeder(
    graph: BoardElectricalGraph,
    *,
    feeder_id: str,
    sub_board_id: str,
    description: str,
    parent_busbar_id: str = "busbar",
) -> BoardElectricalGraph:
    """Add busbar -> feeder device -> cable -> sub-board -> incomer -> busbar."""
    fid = feeder_id.strip()
    child_board_id = sub_board_id.strip()
    child_description = description.strip()
    if not fid:
        raise ValueError("feeder_id is required")
    if not child_board_id:
        raise ValueError("sub_board_id is required")
    if not child_description:
        raise ValueError("sub-board description is required")
    if parent_busbar_id not in graph.node_by_id:
        raise ValueError(f"unknown parent busbar {parent_busbar_id}")
    if graph.node_by_id[parent_busbar_id].kind != "busbar":
        raise ValueError("sub-board feeder parent must be a busbar")
    if any(
        node.circuit_id == fid for node in graph.nodes if node.circuit_id is not None
    ):
        raise ValueError(f"circuit_id {fid} already exists")
    if child_board_id == graph.board_id.strip() or any(
        node.kind == "sub_board" and node.board_ref == child_board_id
        for node in graph.nodes
    ):
        raise ValueError(f"board_id {child_board_id} already exists in hierarchy")

    prefix = f"{fid}:{child_board_id}"
    additions = (
        ElectricalNode(
            f"{fid}:device",
            "protective_device",
            f"{fid} feeder protection",
            parent_busbar_id,
            circuit_id=fid,
        ),
        ElectricalNode(
            f"{fid}:cable",
            "cable",
            f"{fid} feeder cable",
            f"{fid}:device",
            circuit_id=fid,
        ),
        ElectricalNode(
            f"{prefix}:board",
            "sub_board",
            child_description,
            f"{fid}:cable",
            circuit_id=fid,
            board_ref=child_board_id,
        ),
        ElectricalNode(
            f"{prefix}:incomer",
            "incomer",
            f"{child_board_id} incomer",
            f"{prefix}:board",
            board_ref=child_board_id,
        ),
        ElectricalNode(
            f"{prefix}:busbar",
            "busbar",
            f"{child_board_id} busbar",
            f"{prefix}:incomer",
            board_ref=child_board_id,
        ),
    )
    updated = replace(graph, nodes=graph.nodes + additions)
    validate_board_graph(updated)
    return updated


def remove_circuit(graph: BoardElectricalGraph, circuit_id: str) -> BoardElectricalGraph:
    cid = circuit_id.strip()
    roots = tuple(
        node
        for node in graph.nodes
        if node.circuit_id == cid and node.kind == "protective_device"
    )
    if not roots:
        return graph
    remove_ids: set[str] = set()
    for root in roots:
        remove_ids.add(root.node_id)
        remove_ids.update(
            node.node_id for node in graph.descendants_of(root.node_id)
        )
    updated = replace(
        graph,
        nodes=tuple(node for node in graph.nodes if node.node_id not in remove_ids),
    )
    validate_board_graph(updated)
    return updated


def board_plan_request_from_graph(graph: BoardElectricalGraph) -> BoardPlanRequest:
    """Translate root-board final loads into the existing board engine.

    Loads beneath a lightweight field stay inside the root-board calculation. Loads
    beneath a full sub-board are excluded because that board is its own planning
    boundary. Field feeder sizing from downstream aggregate demand is not implemented
    yet and remains explicit rather than inferred.
    """
    validate_board_graph(graph)
    circuits: list[CircuitDesignRequest] = []
    preferences: list[BoardPhasePreference] = []
    for node in graph.nodes:
        if node.kind != "load":
            continue
        if any(
            ancestor.kind == "sub_board"
            for ancestor in graph.ancestors_of(node.node_id)
        ):
            continue
        cid = (node.circuit_id or "").strip()
        if not cid:
            raise ValueError(f"load node {node.node_id} requires circuit_id")
        if node.load_kw is None or node.load_kw <= 0:
            raise ValueError(f"{cid}: load_kw must be greater than 0")
        if node.phase not in ("single", "three"):
            raise ValueError(f"{cid}: phase must be single or three")
        if node.power_factor is None or not 0 < node.power_factor <= 1:
            raise ValueError(
                f"{cid}: power_factor must be greater than 0 and at most 1"
            )
        if node.demand_factor is None or not 0 < node.demand_factor <= 1:
            raise ValueError(
                f"{cid}: demand_factor must be greater than 0 and at most 1"
            )
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

    if not circuits:
        raise ValueError("at least one root-board load circuit is required")
    return BoardPlanRequest(
        board_id=graph.board_id,
        description=graph.description,
        circuits=tuple(circuits),
        line_to_line_voltage_v=graph.line_to_line_voltage_v,
        line_to_neutral_voltage_v=graph.line_to_neutral_voltage_v,
        phase_preferences=tuple(preferences),
    )


def enrich_graph_with_plan(
    graph: BoardElectricalGraph, plan: BoardPlanResult
) -> BoardElectricalGraph:
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
