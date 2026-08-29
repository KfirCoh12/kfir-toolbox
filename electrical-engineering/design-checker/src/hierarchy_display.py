"""Renderer-neutral enrichment of an electrical graph from hierarchy planning results."""
from dataclasses import replace

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph
from .hierarchy_planner import BoardHierarchyPlanResult


def _owning_board_id(graph: BoardElectricalGraph, node: ElectricalNode) -> str | None:
    """Return the nearest upstream board busbar owner for a final-load branch node."""
    start = node
    if node.kind in ("protective_device", "cable") and node.circuit_id:
        loads = tuple(
            candidate
            for candidate in graph.nodes
            if candidate.kind == "load" and candidate.circuit_id == node.circuit_id
        )
        if len(loads) == 1:
            start = loads[0]
    for ancestor in graph.ancestors_of(start.node_id):
        if ancestor.kind == "busbar" and ancestor.board_ref:
            return ancestor.board_ref.strip()
    return None


def enrich_graph_with_hierarchy_plan(
    graph: BoardElectricalGraph,
    hierarchy: BoardHierarchyPlanResult,
) -> BoardElectricalGraph:
    """Apply recursive board plans and feeder roll-ups back to the shared graph.

    This is display/model enrichment only. It does not create new engineering claims:
    board incomers receive the hierarchy planner's provisional conventional candidate,
    sub-board feeder devices receive the matching provisional feeder candidate, and a
    feeder cable is filled only when the hierarchy planner already produced a cable
    candidate from explicitly declared installation conditions.
    """
    validate_board_graph(graph)
    plans = hierarchy.plans_by_board_id
    rollups = {item.feeder_circuit_id: item for item in hierarchy.feeder_rollups}
    rows_by_board = {
        board_id: {row.circuit_id: row for row in plan.schedule_rows}
        for board_id, plan in plans.items()
    }

    enriched: list[ElectricalNode] = []
    for node in graph.nodes:
        if node.kind == "incomer" and node.board_ref:
            plan = plans.get(node.board_ref.strip())
            if plan is not None:
                enriched.append(
                    replace(node, rating_a=plan.incomer_candidate.breaker_rating_a)
                )
                continue

        if node.kind == "sub_board" and node.board_ref:
            plan = plans.get(node.board_ref.strip())
            if plan is not None:
                enriched.append(
                    replace(
                        node,
                        display_detail=f"{plan.phase_balance.max_phase_current_a:.1f} A max",
                    )
                )
                continue

        cid = (node.circuit_id or "").strip()
        feeder = rollups.get(cid) if cid else None
        if feeder is not None:
            if node.kind == "protective_device":
                enriched.append(replace(node, rating_a=feeder.breaker_candidate_a))
                continue
            if node.kind == "cable" and feeder.cable_candidate_mm2 is not None:
                enriched.append(
                    replace(
                        node,
                        cable_mm2=feeder.cable_candidate_mm2,
                        cable_runs=feeder.cable_runs,
                    )
                )
                continue

        owner = _owning_board_id(graph, node) if cid else None
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
