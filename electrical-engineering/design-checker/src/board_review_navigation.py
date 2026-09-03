"""UI-neutral navigation helpers for Board Planner design-review issues."""
from __future__ import annotations


def branch_uid_for_route_id(board: dict, route_id: str | None) -> str | None:
    """Return the editable branch uid that owns a circuit/feeder route identifier.

    Final circuits are matched by ``circuit_id``. Field and sub-board branches are
    matched by their feeder IDs. The helper does not inspect calculated graph nodes,
    so UI navigation remains separate from engineering calculations.
    """
    target = str(route_id or "").strip()
    if not target:
        return None

    branches = board.get("branches", [])
    if not isinstance(branches, list):
        raise ValueError("working board branches must be a list")

    matches: list[str] = []
    for branch in branches:
        if not isinstance(branch, dict):
            continue
        kind = str(branch.get("kind", ""))
        candidate = (
            str(branch.get("circuit_id", "")).strip()
            if kind == "final"
            else str(branch.get("feeder_id", "")).strip()
        )
        if candidate == target:
            matches.append(str(branch.get("uid", "")).strip())

    matches = [uid for uid in matches if uid]
    if len(matches) > 1:
        raise ValueError(f"route identifier {target} belongs to multiple planner branches")
    return matches[0] if matches else None
