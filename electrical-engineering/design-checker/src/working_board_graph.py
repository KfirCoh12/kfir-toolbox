"""Reconstruct the Board Planner topology from its persisted working-board payload.

This module is intentionally UI-neutral. It lets secondary pages consume the same
saved hierarchy without importing or executing Streamlit page code.
"""
from .board_graph import (
    BoardElectricalGraph,
    add_field_feeder,
    add_radial_circuit,
    add_sub_board_feeder,
    make_radial_board_graph,
)


def graph_from_working_board(payload: dict) -> BoardElectricalGraph:
    """Build the saved board hierarchy without inventing calculated design results."""
    if not isinstance(payload, dict):
        raise ValueError("working board payload must be a mapping")

    board_id = str(payload.get("board_id", "")).strip()
    description = str(payload.get("description", "")).strip()
    if not board_id or not description:
        raise ValueError("working board requires board_id and description")

    try:
        voltage_ll = float(payload.get("line_to_line_voltage_v", 400.0))
        voltage_ln = float(payload.get("line_to_neutral_voltage_v", 230.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("working board supply voltages must be numeric") from exc

    branches = payload.get("branches", [])
    if not isinstance(branches, list):
        raise ValueError("working board branches must be a list")

    graph = make_radial_board_graph(
        board_id=board_id,
        description=description,
        line_to_line_voltage_v=voltage_ll,
        line_to_neutral_voltage_v=voltage_ln,
    )
    busbar_by_parent_key = {"root": "busbar"}

    for branch in branches:
        if not isinstance(branch, dict):
            raise ValueError("each working-board branch must be a mapping")
        uid = str(branch.get("uid", "")).strip()
        kind = str(branch.get("kind", "")).strip()
        if not uid or not kind:
            raise ValueError("each working-board branch requires uid and kind")

        parent_key = str(branch.get("parent_key", "root"))
        parent_busbar_id = busbar_by_parent_key.get(parent_key)
        if parent_busbar_id is None:
            raise ValueError(f"Branch {uid} references an unavailable parent hierarchy node.")

        if kind == "final":
            circuit_id = str(branch.get("circuit_id", "")).strip()
            branch_description = str(branch.get("description", "")).strip()
            if not circuit_id or not branch_description:
                raise ValueError(f"Final branch {uid} requires circuit_id and description")
            mode = str(branch.get("mode", "auto"))
            load_kw = None if mode == "manual" else float(branch.get("load_kw", 0.0))
            graph = add_radial_circuit(
                graph,
                circuit_id=circuit_id,
                description=branch_description,
                load_kw=load_kw,
                phase=str(branch.get("phase", "three")),
                power_factor=float(branch.get("power_factor", 1.0)),
                demand_factor=float(branch.get("demand_factor", 1.0)),
                material=str(branch.get("material", "copper")),
                phase_preference=str(branch.get("phase_preference", "Auto")),
                display_detail="Manual · saved outlet basis" if mode == "manual" else None,
                parent_busbar_id=parent_busbar_id,
            )
        elif kind == "field":
            feeder_id = str(branch.get("feeder_id", "")).strip()
            field_id = str(branch.get("field_id", "")).strip()
            branch_description = str(branch.get("description", "")).strip()
            if not feeder_id or not field_id or not branch_description:
                raise ValueError(f"Field branch {uid} requires feeder_id, field_id and description")
            graph = add_field_feeder(
                graph,
                feeder_id=feeder_id,
                field_id=field_id,
                description=branch_description,
                parent_busbar_id=parent_busbar_id,
            )
            busbar_by_parent_key[uid] = f"{feeder_id}:{field_id}:busbar"
        elif kind == "sub_board":
            feeder_id = str(branch.get("feeder_id", "")).strip()
            sub_board_id = str(branch.get("sub_board_id", "")).strip()
            branch_description = str(branch.get("description", "")).strip()
            if not feeder_id or not sub_board_id or not branch_description:
                raise ValueError(
                    f"Sub-board branch {uid} requires feeder_id, sub_board_id and description"
                )
            graph = add_sub_board_feeder(
                graph,
                feeder_id=feeder_id,
                sub_board_id=sub_board_id,
                description=branch_description,
                parent_busbar_id=parent_busbar_id,
            )
            busbar_by_parent_key[uid] = f"{feeder_id}:{sub_board_id}:busbar"
        else:
            raise ValueError(f"Unsupported branch type: {kind}")

    return graph
