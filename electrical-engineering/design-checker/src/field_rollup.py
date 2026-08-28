"""Bottom-up planning roll-up for lightweight circuit fields.

A field remains inside its owning board calculation boundary. The board engine has
already calculated and phase-allocated the final circuits; this module reuses those
results to derive the electrical demand seen by the field feeder without counting the
feeder as an additional board load.

The feeder candidate is deliberately planning-only. Its required current is the
highest allocated downstream phase current, with no extra diversity. The existing
three-phase circuit engine is then reused for a provisional breaker/cable candidate.
Protection/selectivity and mixed single-phase neutral/harmonic effects are not
silently claimed as verified.
"""
from dataclasses import dataclass, replace
from typing import Literal

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph
from .board_planner import BoardPlanResult
from .circuit_engine import CircuitDesignRequest, CircuitDesignResult, calculate_circuit_design

FieldRollupStatus = Literal["PROVISIONAL", "EMPTY", "OUTSIDE_PLAN_BOUNDARY"]


@dataclass(frozen=True)
class FieldPhaseDemand:
    l1_current_a: float
    l2_current_a: float
    l3_current_a: float

    @property
    def max_phase_current_a(self) -> float:
        return max(self.l1_current_a, self.l2_current_a, self.l3_current_a)


@dataclass(frozen=True)
class FieldFeederRollup:
    field_node_id: str
    field_ref: str
    feeder_circuit_id: str
    status: FieldRollupStatus
    descendant_circuit_ids: tuple[str, ...]
    phase_demand: FieldPhaseDemand
    feeder_design: CircuitDesignResult | None
    contains_single_phase_loads: bool
    limitations: tuple[str, ...]

    @property
    def required_current_a(self) -> float:
        return self.phase_demand.max_phase_current_a


def _field_is_below_sub_board(graph: BoardElectricalGraph, field: ElectricalNode) -> bool:
    return any(ancestor.kind == "sub_board" for ancestor in graph.ancestors_of(field.node_id))


def _descendant_load_circuit_ids(
    graph: BoardElectricalGraph,
    field: ElectricalNode,
    plan: BoardPlanResult,
) -> tuple[str, ...]:
    plan_ids = {c.request.circuit_id for c in plan.circuits}
    result: list[str] = []
    for node in graph.descendants_of(field.node_id):
        if node.kind != "load" or not node.circuit_id:
            continue
        # A downstream full board is a separate calculation boundary and must not be
        # flattened into this lightweight field roll-up.
        ancestors = graph.ancestors_of(node.node_id)
        before_field: list[ElectricalNode] = []
        for ancestor in ancestors:
            if ancestor.node_id == field.node_id:
                break
            before_field.append(ancestor)
        if any(ancestor.kind == "sub_board" for ancestor in before_field):
            continue
        if node.circuit_id in plan_ids:
            result.append(node.circuit_id)
    return tuple(result)


def _phase_demand(plan: BoardPlanResult, circuit_ids: tuple[str, ...]) -> FieldPhaseDemand:
    allocations = {allocation.circuit_id: allocation for allocation in plan.phase_balance.allocations}
    l1 = l2 = l3 = 0.0
    for circuit_id in circuit_ids:
        allocation = allocations[circuit_id]
        current = allocation.design_current_a
        if allocation.assigned_phase == "3P":
            l1 += current
            l2 += current
            l3 += current
        elif allocation.assigned_phase == "L1":
            l1 += current
        elif allocation.assigned_phase == "L2":
            l2 += current
        elif allocation.assigned_phase == "L3":
            l3 += current
        else:  # pragma: no cover - BoardPhaseAllocation guards this contract.
            raise ValueError(f"unsupported field phase allocation {allocation.assigned_phase}")
    return FieldPhaseDemand(l1, l2, l3)


def calculate_field_rollups(
    graph: BoardElectricalGraph,
    plan: BoardPlanResult,
) -> tuple[FieldFeederRollup, ...]:
    """Calculate one planning feeder roll-up for every field in the plan boundary."""
    validate_board_graph(graph)
    if plan.request.board_id.strip() != graph.board_id.strip():
        raise ValueError("board plan does not belong to this graph")

    circuit_results = {c.request.circuit_id: c for c in plan.circuits}
    rollups: list[FieldFeederRollup] = []
    for field in (node for node in graph.nodes if node.kind == "field"):
        field_ref = (field.field_ref or "").strip()
        feeder_id = (field.circuit_id or "").strip()
        if not field_ref or not feeder_id:
            raise ValueError(f"field node {field.node_id} requires field_ref and feeder circuit_id")

        if _field_is_below_sub_board(graph, field):
            rollups.append(FieldFeederRollup(
                field.node_id,
                field_ref,
                feeder_id,
                "OUTSIDE_PLAN_BOUNDARY",
                tuple(),
                FieldPhaseDemand(0.0, 0.0, 0.0),
                None,
                False,
                ("Field belongs to a downstream sub-board calculation boundary.",),
            ))
            continue

        circuit_ids = _descendant_load_circuit_ids(graph, field, plan)
        demand = _phase_demand(plan, circuit_ids)
        if not circuit_ids:
            rollups.append(FieldFeederRollup(
                field.node_id,
                field_ref,
                feeder_id,
                "EMPTY",
                tuple(),
                demand,
                None,
                False,
                ("Field has no calculated final circuits in this board boundary.",),
            ))
            continue

        if field.material not in ("copper", "aluminium"):
            raise ValueError(f"field {field_ref} requires a feeder conductor material")
        contains_single_phase = any(
            circuit_results[circuit_id].request.phase == "single"
            for circuit_id in circuit_ids
        )
        feeder = calculate_circuit_design(CircuitDesignRequest(
            circuit_id=feeder_id,
            description=f"{field.label} feeder",
            load_type="a",
            load_value=demand.max_phase_current_a,
            voltage_v=graph.line_to_line_voltage_v,
            phase="three",
            power_factor=None,
            demand_factor=1.0,
            material=field.material,
        ))
        limitations = [
            "Field feeder current is the highest planned downstream phase current; no additional field diversity is applied.",
            "Field feeder breaker/cable values are planning candidates; protection and selectivity are not verified.",
        ]
        if contains_single_phase:
            limitations.append(
                "The cable candidate reuses the three-loaded-conductor Method E route; neutral loading and harmonic effects for single-phase child circuits are not verified."
            )
        rollups.append(FieldFeederRollup(
            field.node_id,
            field_ref,
            feeder_id,
            "PROVISIONAL",
            circuit_ids,
            demand,
            feeder,
            contains_single_phase,
            tuple(limitations),
        ))
    return tuple(rollups)


def enrich_graph_with_field_rollups(
    graph: BoardElectricalGraph,
    rollups: tuple[FieldFeederRollup, ...],
) -> BoardElectricalGraph:
    """Write field feeder candidates onto existing hidden feeder nodes for the SLD."""
    by_rollup = {rollup.field_node_id: rollup for rollup in rollups}
    if len(by_rollup) != len(rollups):
        raise ValueError("field rollups must have unique field_node_id values")

    enriched: list[ElectricalNode] = []
    for node in graph.nodes:
        if node.kind == "field":
            rollup = by_rollup.get(node.node_id)
            if rollup is None or rollup.status != "PROVISIONAL" or rollup.feeder_design is None:
                enriched.append(node)
                continue
            detail = f"{len(rollup.descendant_circuit_ids)} circuits · {rollup.required_current_a:.1f} A max"
            enriched.append(replace(
                node,
                display_detail=detail,
                scope_status="PARTIAL_SCOPE",
                issue_codes=tuple(dict.fromkeys(node.issue_codes + ("FIELD_FEEDER_PROVISIONAL",))),
            ))
            continue

        rollup = next(
            (item for item in rollups if item.feeder_circuit_id == node.circuit_id and item.status == "PROVISIONAL"),
            None,
        )
        if rollup is None or rollup.feeder_design is None:
            enriched.append(node)
            continue
        if node.kind == "protective_device":
            enriched.append(replace(
                node,
                rating_a=rollup.feeder_design.breaker_a,
                scope_status="PARTIAL_SCOPE",
                issue_codes=tuple(dict.fromkeys(node.issue_codes + ("FIELD_FEEDER_PROVISIONAL",))),
            ))
        elif node.kind == "cable":
            enriched.append(replace(
                node,
                cable_mm2=rollup.feeder_design.cable_mm2,
                cable_runs=rollup.feeder_design.cable_runs,
                scope_status="PARTIAL_SCOPE",
                issue_codes=tuple(dict.fromkeys(node.issue_codes + ("FIELD_FEEDER_PROVISIONAL",))),
            ))
        else:
            enriched.append(node)

    updated = replace(graph, nodes=tuple(enriched))
    validate_board_graph(updated)
    return updated
