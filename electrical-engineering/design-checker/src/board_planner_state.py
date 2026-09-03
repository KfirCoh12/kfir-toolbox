"""UI-neutral working-board mutation helpers for Board Planner.

The Board Planner owns only structural/design-input fields in the shared working-board
record. Protection/fault-study metadata is deliberately omitted from
``planner_owned_payload`` so autosaves cannot overwrite data maintained by other pages.
"""
from __future__ import annotations

from copy import deepcopy

_PLANNER_OWNED_KEYS = (
    "board_id",
    "description",
    "line_to_line_voltage_v",
    "line_to_neutral_voltage_v",
    "branches",
    "uid_counter",
    "selected_node",
)


def planner_owned_payload(board: dict) -> dict:
    """Return only the top-level fields owned by Board Planner."""
    return {key: deepcopy(board[key]) for key in _PLANNER_OWNED_KEYS if key in board}


def _next_uid(board: dict) -> str:
    current = int(board.get("uid_counter", 100)) + 1
    board["uid_counter"] = current
    return f"b{current}"


def _next_id(board: dict, prefix: str, key: str) -> str:
    used = {
        str(item.get(key, "")).strip()
        for item in board.get("branches", [])
        if isinstance(item, dict)
    }
    number = 1
    while f"{prefix}-{number:02d}" in used:
        number += 1
    return f"{prefix}-{number:02d}"


def add_planner_branch(board: dict, kind: str, parent_key: str = "root") -> str:
    """Append one hierarchy-valid branch and return its new uid."""
    if kind not in ("circuit", "field", "sub_board"):
        raise ValueError(f"Unsupported planner branch kind: {kind}")
    branches = board.setdefault("branches", [])
    if not isinstance(branches, list):
        raise ValueError("working board branches must be a list")

    uid = _next_uid(board)
    if kind == "circuit":
        circuit_id = _next_id(board, "C", "circuit_id")
        branches.append(
            {
                "uid": uid,
                "kind": "final",
                "parent_key": parent_key,
                "circuit_id": circuit_id,
                "description": "New circuit",
                "mode": "auto",
                "load_kw": 5.0,
                "phase": "three",
                "power_factor": 0.9,
                "demand_factor": 1.0,
                "material": "copper",
                "phase_preference": "Auto",
                "connection_option_id": None,
            }
        )
    elif kind == "field":
        branches.append(
            {
                "uid": uid,
                "kind": "field",
                "parent_key": parent_key,
                "feeder_id": _next_id(board, "F", "feeder_id"),
                "field_id": _next_id(board, "FIELD", "field_id"),
                "description": "New field",
                "material": "copper",
            }
        )
    else:
        branches.append(
            {
                "uid": uid,
                "kind": "sub_board",
                "parent_key": parent_key,
                "feeder_id": _next_id(board, "SB", "feeder_id"),
                "sub_board_id": _next_id(board, "DB", "sub_board_id"),
                "description": "New sub-board",
                "material": "copper",
            }
        )
    return uid


def remove_planner_branch_tree(board: dict, uid: str) -> tuple[str, ...]:
    """Remove a selected branch and every descendant, returning removed uids."""
    branches = board.get("branches", [])
    if not isinstance(branches, list):
        raise ValueError("working board branches must be a list")

    existing = {str(item.get("uid")) for item in branches if isinstance(item, dict)}
    if uid not in existing:
        return tuple()

    removed = {uid}
    changed = True
    while changed:
        changed = False
        for item in branches:
            if not isinstance(item, dict):
                continue
            item_uid = str(item.get("uid"))
            if str(item.get("parent_key", "root")) in removed and item_uid not in removed:
                removed.add(item_uid)
                changed = True

    board["branches"] = [
        item
        for item in branches
        if not isinstance(item, dict) or str(item.get("uid")) not in removed
    ]
    return tuple(sorted(removed))
