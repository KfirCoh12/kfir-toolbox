"""Apply recursive board-planning results back to the electrical hierarchy graph.

This module is renderer-neutral. It writes only values that the hierarchy planner has
actually calculated:

- final-circuit schedule results -> existing protection/cable/load nodes,
- each calculated board's provisional incomer candidate -> that board incomer,
- downstream-board feeder breaker candidate -> existing feeder protective device,
- explicitly calculated downstream-board feeder cable candidate -> existing feeder cable.

A sub-board feeder cable is populated only when the hierarchy planner returned a
candidate from an explicit feeder-installation declaration. Undeclared or unsupported
feeder cables remain unsized. Protection/selectivity/fault-level verification is not
implied by this enrichment.
"""
from dataclasses import replace

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph
from .hierarchy_planner import BoardHierarchyPlanResult

_PROVISIONAL_FEEDER_CODE = "SUB_BOARD_FEEDER_PROVISIONAL"
_PROVISIONAL_FEEDER_CABLE_CODE = "SUB_BOARD_FEEDER_CABLE_PROVISIONAL"
_PROVISIONAL_INCOMER_CODE = "BOARD_INCOMER_PROVISIONAL"


def _board_incomers(graph: BoardElectricalGraph) -> dict[str, str]:
    """Return exactly one incomer node id for every board represented by a busbar."""
    result: dict[str, str] = {}
    for busbar in (node for node in graph.nodes if node.kind == "busbar" and node.board_ref):
        board_id = busbar.board_ref.strip()
        if not board_id:
            raise ValueError(f"busbar {busbar.node_id} requires board_ref")
        parent = graph.node_by_id.get(busbar.parent_id) if busbar.parent_id else None
        if parent is None or parent.kind != "incomer":
            raise ValueError(f"board busbar {busbar.node_id} must be directly fed by an incomer")
        if board_id in result:
            raise ValueError(f"board {board_id} has multiple incomers in hierarchy")
        result[board_id] = parent.node_id
    return result


def _load_owner_board(graph: BoardElectricalGraph, load: ElectricalNode) -> str:
    for ancestor in graph.ancestors_of(load.node_id):
        if ancestor.kind == "busbar" and ancestor.board_ref:
            return ancestor.board_ref.strip()
    raise ValueError(f"load {load.node_id} is not downstream of a board busbar")


def _validate_result_against_graph(
    graph: BoardElectricalGraph,
    result: BoardHierarchyPlanResult,
) -> tuple[dict[str, str], dict[str, tuple[str, object]]]:
    incomer_by_board = _board_incomers(graph)
    result_board_ids = [board.board_id.strip() for board in result.boards]
    if any(not board_id for board_id in result_board_ids):
        raise ValueError("hierarchy result board_id is required")
    if len(result_board_ids) != len(set(result_board_ids)):
        raise ValueError("hierarchy result contains duplicate board_id values")
    if set(result_board_ids) != set(incomer_by_board):
        raise ValueError("hierarchy result boards do not match graph board hierarchy")

    graph_loads = {
        node.circuit_id.strip(): node
        for node in graph.nodes
        if node.kind == "load" and node.circuit_id
    }
    rows_by_circuit: dict[str, tuple[str, object]] = {}
    for board in result.boards:
        board_id = board.board_id.strip()
        if board.plan is None:
            if board.status != "NO_DEMAND":
                raise ValueError(f"board {board_id} has no plan but is not marked NO_DEMAND")
            continue
        if board.plan.request.board_id.strip() != board_id:
            raise ValueError(f"board plan {board.plan.request.board_id} does not match {board_id}")
        for row in board.plan.schedule_rows:
            cid = row.circuit_id.strip()
            load = graph_loads.get(cid)
            if load is None:
                raise ValueError(f"hierarchy plan circuit {cid} is not a graph final load")
            owner = _load_owner_board(graph, load)
            if owner != board_id:
                raise ValueError(
                    f"hierarchy plan circuit {cid} belongs to board {owner}, not {board_id}"
                )
            if cid in rows_by_circuit:
                raise ValueError(f"hierarchy plan contains duplicate final circuit {cid}")
            rows_by_circuit[cid] = (board_id, row)

    rollup_by_feeder: dict[str, object] = {}
    graph_feeder_devices = {
        node.circuit_id.strip(): node
        for node in graph.nodes
        if node.kind == "protective_device" and node.circuit_id
    }
    graph_feeder_cables = {
        node.circuit_id.strip(): node
        for node in graph.nodes
        if node.kind == "cable" and node.circuit_id
    }
    for rollup in result.feeder_rollups:
        feeder_id = rollup.feeder_circuit_id.strip()
        if not feeder_id:
            raise ValueError("sub-board feeder rollup feeder_circuit_id is required")
        if feeder_id in rollup_by_feeder:
            raise ValueError(f"duplicate sub-board feeder rollup for {feeder_id}")
        device = graph_feeder_devices.get(feeder_id)
        if device is None:
            raise ValueError(f"sub-board feeder rollup {feeder_id} has no graph protective device")
        cable = graph_feeder_cables.get(feeder_id)
        if cable is None or cable.parent_id != device.node_id:
            raise ValueError(f"sub-board feeder rollup {feeder_id} has no matching graph cable")
        downstream = tuple(
            node
            for node in graph.nodes
            if node.kind == "sub_board"
            and node.circuit_id == feeder_id
            and node.board_ref == rollup.board_id
        )
        if len(downstream) != 1:
            raise ValueError(
                f"sub-board feeder rollup {feeder_id} does not match exactly one downstream board"
            )
        if rollup.cable_status == "CANDIDATE":
            if rollup.cable_candidate_mm2 is None or rollup.cable_runs is None:
                raise ValueError(
                    f"sub-board feeder rollup {feeder_id} cable candidate is incomplete"
                )
        elif rollup.cable_candidate_mm2 is not None or rollup.cable_runs is not None:
            raise ValueError(
                f"sub-board feeder rollup {feeder_id} exposes cable values without CANDIDATE status"
            )
        rollup_by_feeder[feeder_id] = rollup

    return incomer_by_board, rows_by_circuit


def enrich_graph_with_hierarchy_plan(
    graph: BoardElectricalGraph,
    result: BoardHierarchyPlanResult,
) -> BoardElectricalGraph:
    """Return a graph enriched with all supported recursive hierarchy planning values."""
    validate_board_graph(graph)
    incomer_by_board, rows_by_circuit = _validate_result_against_graph(graph, result)
    plan_by_board = {
        board.board_id.strip(): board.plan
        for board in result.boards
        if board.plan is not None
    }
    rollup_by_feeder = {
        rollup.feeder_circuit_id.strip(): rollup for rollup in result.feeder_rollups
    }

    enriched: list[ElectricalNode] = []
    for node in graph.nodes:
        # Final-circuit calculation results.
        cid = node.circuit_id.strip() if node.circuit_id else None
        row_entry = rows_by_circuit.get(cid) if cid else None
        if row_entry is not None:
            _, row = row_entry
            common = dict(
                assigned_phase=row.assigned_phase,
                scope_status=row.scope_status,
                issue_codes=row.blocking_issue_codes,
            )
            if node.kind == "protective_device":
                enriched.append(replace(node, rating_a=row.breaker_a, **common))
                continue
            if node.kind == "cable":
                enriched.append(
                    replace(
                        node,
                        cable_mm2=row.cable_mm2,
                        cable_runs=row.cable_runs,
                        **common,
                    )
                )
                continue
            if node.kind == "load":
                enriched.append(replace(node, **common))
                continue

        # Board incomer candidates. These remain explicitly provisional.
        board_id = next(
            (key for key, incomer_id in incomer_by_board.items() if incomer_id == node.node_id),
            None,
        )
        if board_id is not None:
            plan = plan_by_board.get(board_id)
            if plan is None:
                enriched.append(node)
                continue
            candidate = plan.incomer_candidate
            enriched.append(
                replace(
                    node,
                    rating_a=candidate.breaker_rating_a,
                    scope_status="PARTIAL_SCOPE",
                    issue_codes=tuple(
                        dict.fromkeys(node.issue_codes + (_PROVISIONAL_INCOMER_CODE,))
                    ),
                )
            )
            continue

        rollup = rollup_by_feeder.get(cid) if cid else None

        # Upstream protection for a downstream board.
        if node.kind == "protective_device" and rollup is not None:
            enriched.append(
                replace(
                    node,
                    rating_a=rollup.breaker_candidate_a,
                    scope_status="PARTIAL_SCOPE" if rollup.status != "NO_DEMAND" else node.scope_status,
                    issue_codes=(
                        tuple(dict.fromkeys(node.issue_codes + (_PROVISIONAL_FEEDER_CODE,)))
                        if rollup.status != "NO_DEMAND"
                        else node.issue_codes
                    ),
                )
            )
            continue

        # Feeder cable values exist only after an explicit supported installation declaration.
        if node.kind == "cable" and rollup is not None and rollup.cable_status == "CANDIDATE":
            graph_scope = (
                "NOT_VERIFIED"
                if rollup.feeder_scope_status == "NOT_VERIFIED"
                else "PARTIAL_SCOPE"
            )
            enriched.append(
                replace(
                    node,
                    cable_mm2=rollup.cable_candidate_mm2,
                    cable_runs=rollup.cable_runs,
                    scope_status=graph_scope,
                    issue_codes=tuple(
                        dict.fromkeys(node.issue_codes + (_PROVISIONAL_FEEDER_CABLE_CODE,))
                    ),
                )
            )
            continue

        enriched.append(node)

    updated = replace(graph, nodes=tuple(enriched))
    validate_board_graph(updated)
    return updated
