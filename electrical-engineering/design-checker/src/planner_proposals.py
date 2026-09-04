"""Safe proposal engine for AI-assisted Board Planner changes.

An assistant never writes arbitrary board JSON. It creates a proposal made of a small
set of validated operations. The proposal is previewed against a detached board,
recalculated through the existing engineering engine, and can only be applied if the
project revision has not changed since the proposal was created.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Literal

from .board_planner_state import add_planner_branch, remove_planner_branch_tree
from .design_review import DesignReviewSummary, design_review_summary
from .project_state import project_state_from_payload
from .working_board_graph import graph_from_working_board
from .working_board_plan import CalculatedWorkingBoard, calculate_working_board

ProposalStatus = Literal["PENDING", "APPLIED", "REJECTED"]
OperationKind = Literal[
    "ADD_BRANCH",
    "UPDATE_BRANCH",
    "MOVE_BRANCH",
    "REMOVE_BRANCH",
    "UPDATE_BOARD",
]

_OPERATION_KINDS = {
    "ADD_BRANCH",
    "UPDATE_BRANCH",
    "MOVE_BRANCH",
    "REMOVE_BRANCH",
    "UPDATE_BOARD",
}
_BRANCH_KINDS = {"circuit", "field", "sub_board"}
_BOARD_FIELDS = {
    "board_id",
    "description",
    "line_to_line_voltage_v",
    "line_to_neutral_voltage_v",
}
_BRANCH_FIELDS = {
    "final": {
        "circuit_id",
        "description",
        "mode",
        "load_kw",
        "phase",
        "power_factor",
        "demand_factor",
        "material",
        "phase_preference",
        "connection_option_id",
    },
    "field": {"feeder_id", "field_id", "description", "material"},
    "sub_board": {"feeder_id", "sub_board_id", "description", "material"},
}


def _text(value, label: str) -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f"{label} is required")
    return result


def _branch_by_uid(board: dict, uid: str) -> dict:
    branches = board.get("branches", [])
    if not isinstance(branches, list):
        raise ValueError("working board branches must be a list")
    branch = next(
        (item for item in branches if isinstance(item, dict) and str(item.get("uid")) == uid),
        None,
    )
    if branch is None:
        raise ValueError(f"Unknown planner branch uid: {uid}")
    return branch


def _child_kind_for_branch(branch: dict) -> str:
    kind = str(branch.get("kind"))
    if kind == "final":
        return "circuit"
    if kind in ("field", "sub_board"):
        return kind
    raise ValueError(f"Unsupported existing branch kind: {kind}")


def _allowed_children(parent: dict | None) -> set[str]:
    if parent is None:
        return {"circuit", "field", "sub_board"}
    kind = str(parent.get("kind"))
    if kind == "final":
        return set()
    if kind == "field":
        return {"circuit", "sub_board"}
    if kind == "sub_board":
        return {"circuit", "field", "sub_board"}
    raise ValueError(f"Unsupported parent branch kind: {kind}")


def _resolve_uid(value, refs: dict[str, str], label: str) -> str:
    text = _text(value, label)
    if text == "root":
        return text
    if text.startswith("@"):
        ref = text[1:]
        if ref not in refs:
            raise ValueError(f"Unknown proposal branch reference: @{ref}")
        return refs[ref]
    return text


def _validate_values(kind: str, values) -> dict:
    if values is None:
        return {}
    if not isinstance(values, dict):
        raise ValueError("proposal operation values must be an object")
    allowed = _BRANCH_FIELDS[kind]
    unsupported = set(values) - allowed
    if unsupported:
        raise ValueError(
            f"Unsupported {kind} proposal fields: {', '.join(sorted(unsupported))}"
        )
    return deepcopy(values)


def _descendant_uids(board: dict, uid: str) -> set[str]:
    branches = board.get("branches", [])
    descendants = {uid}
    changed = True
    while changed:
        changed = False
        for item in branches:
            if not isinstance(item, dict):
                continue
            item_uid = str(item.get("uid"))
            if str(item.get("parent_key", "root")) in descendants and item_uid not in descendants:
                descendants.add(item_uid)
                changed = True
    return descendants


def normalize_proposal_operations(operations) -> tuple[dict, ...]:
    if not isinstance(operations, (list, tuple)) or not operations:
        raise ValueError("A proposal requires at least one operation")

    normalized: list[dict] = []
    refs: set[str] = set()
    for raw in operations:
        if not isinstance(raw, dict):
            raise ValueError("proposal operations must be objects")
        kind = str(raw.get("kind", "")).strip().upper()
        if kind not in _OPERATION_KINDS:
            raise ValueError(f"Unsupported proposal operation: {kind or '<blank>'}")

        item = deepcopy(raw)
        item["kind"] = kind
        if kind == "ADD_BRANCH":
            branch_kind = str(item.get("branch_kind", "")).strip()
            if branch_kind not in _BRANCH_KINDS:
                raise ValueError("ADD_BRANCH requires circuit, field or sub_board branch_kind")
            item["branch_kind"] = branch_kind
            item["parent_uid"] = _text(item.get("parent_uid", "root"), "parent_uid")
            ref = str(item.get("ref", "")).strip()
            if ref:
                if ref.startswith("@"):
                    ref = ref[1:]
                if ref in refs:
                    raise ValueError(f"Duplicate proposal branch reference: {ref}")
                refs.add(ref)
                item["ref"] = ref
            elif "ref" in item:
                item.pop("ref")
            target_kind = "final" if branch_kind == "circuit" else branch_kind
            item["values"] = _validate_values(target_kind, item.get("values"))
        elif kind == "UPDATE_BRANCH":
            item["target_uid"] = _text(item.get("target_uid"), "target_uid")
            if not isinstance(item.get("values"), dict) or not item["values"]:
                raise ValueError("UPDATE_BRANCH requires non-empty values")
        elif kind == "MOVE_BRANCH":
            item["target_uid"] = _text(item.get("target_uid"), "target_uid")
            item["new_parent_uid"] = _text(item.get("new_parent_uid", "root"), "new_parent_uid")
        elif kind == "REMOVE_BRANCH":
            item["target_uid"] = _text(item.get("target_uid"), "target_uid")
        else:
            values = item.get("values")
            if not isinstance(values, dict) or not values:
                raise ValueError("UPDATE_BOARD requires non-empty values")
            unsupported = set(values) - _BOARD_FIELDS
            if unsupported:
                raise ValueError(
                    f"Unsupported board proposal fields: {', '.join(sorted(unsupported))}"
                )
            item["values"] = deepcopy(values)
        normalized.append(item)
    return tuple(normalized)


def apply_proposal_operations(board: dict, operations) -> dict:
    """Apply validated proposal operations to a detached board and recalculate validity."""
    working = deepcopy(board)
    refs: dict[str, str] = {}

    for operation in normalize_proposal_operations(operations):
        kind = operation["kind"]
        if kind == "ADD_BRANCH":
            parent_uid = _resolve_uid(operation["parent_uid"], refs, "parent_uid")
            parent = None if parent_uid == "root" else _branch_by_uid(working, parent_uid)
            branch_kind = operation["branch_kind"]
            if branch_kind not in _allowed_children(parent):
                raise ValueError(
                    f"{branch_kind} cannot be added below "
                    + ("root" if parent is None else str(parent.get("kind")))
                )
            uid = add_planner_branch(working, branch_kind, parent_uid)
            created = _branch_by_uid(working, uid)
            created_kind = str(created.get("kind"))
            created.update(_validate_values(created_kind, operation.get("values")))
            ref = operation.get("ref")
            if ref:
                refs[str(ref)] = uid

        elif kind == "UPDATE_BRANCH":
            target_uid = _resolve_uid(operation["target_uid"], refs, "target_uid")
            branch = _branch_by_uid(working, target_uid)
            branch_kind = str(branch.get("kind"))
            branch.update(_validate_values(branch_kind, operation["values"]))

        elif kind == "MOVE_BRANCH":
            target_uid = _resolve_uid(operation["target_uid"], refs, "target_uid")
            new_parent_uid = _resolve_uid(operation["new_parent_uid"], refs, "new_parent_uid")
            branch = _branch_by_uid(working, target_uid)
            if new_parent_uid in _descendant_uids(working, target_uid):
                raise ValueError("A planner branch cannot be moved below itself or its descendant")
            parent = None if new_parent_uid == "root" else _branch_by_uid(working, new_parent_uid)
            child_kind = _child_kind_for_branch(branch)
            if child_kind not in _allowed_children(parent):
                raise ValueError(
                    f"{child_kind} cannot be moved below "
                    + ("root" if parent is None else str(parent.get("kind")))
                )
            branch["parent_key"] = new_parent_uid

        elif kind == "REMOVE_BRANCH":
            target_uid = _resolve_uid(operation["target_uid"], refs, "target_uid")
            if not remove_planner_branch_tree(working, target_uid):
                raise ValueError(f"Unknown planner branch uid: {target_uid}")

        else:
            working.update(deepcopy(operation["values"]))

    # Validate graph topology for every proposal, including an otherwise empty board.
    graph_from_working_board(working)
    finals = [
        item
        for item in working.get("branches", [])
        if isinstance(item, dict) and item.get("kind") == "final"
    ]
    if finals:
        calculate_working_board(working)
    return working


def _proposal_by_id(state: dict, proposal_id: str) -> dict:
    pid = _text(proposal_id, "proposal_id")
    proposal = next((item for item in state["proposals"] if item.get("proposal_id") == pid), None)
    if proposal is None:
        raise ValueError(f"Unknown board proposal: {pid}")
    return proposal


def create_board_proposal(
    payload: dict,
    *,
    title: str,
    reason: str,
    operations,
    assumptions: tuple[str, ...] = tuple(),
) -> tuple[dict, str]:
    """Create and validate a pending proposal without altering the working board."""
    normalized = normalize_proposal_operations(operations)
    # Preview validation must succeed before the proposal can enter project state.
    apply_proposal_operations(payload, normalized)

    updated = deepcopy(payload)
    state = project_state_from_payload(updated)
    state["proposal_counter"] += 1
    proposal_id = f"P-{state['proposal_counter']:03d}"
    state["proposals"].append(
        {
            "proposal_id": proposal_id,
            "status": "PENDING",
            "base_revision": state["revision"],
            "title": _text(title, "proposal title"),
            "reason": _text(reason, "proposal reason"),
            "operations": [deepcopy(item) for item in normalized],
            "assumptions": [
                str(item).strip() for item in assumptions if str(item).strip()
            ],
        }
    )
    updated["project_state"] = state
    return updated, proposal_id


def preview_board_proposal(
    payload: dict,
    proposal_id: str,
) -> tuple[dict, CalculatedWorkingBoard | None, DesignReviewSummary | None]:
    state = project_state_from_payload(payload)
    proposal = _proposal_by_id(state, proposal_id)
    if proposal.get("status") != "PENDING":
        raise ValueError(f"Proposal {proposal_id} is not pending")
    if int(proposal.get("base_revision", -1)) != int(state["revision"]):
        raise ValueError(
            f"Proposal {proposal_id} is stale: project revision changed after it was created"
        )
    board = apply_proposal_operations(payload, proposal["operations"])
    finals = [
        item
        for item in board.get("branches", [])
        if isinstance(item, dict) and item.get("kind") == "final"
    ]
    if not finals:
        return board, None, None
    calculated = calculate_working_board(board)
    return board, calculated, design_review_summary(calculated)


def apply_board_proposal(payload: dict, proposal_id: str) -> dict:
    """Apply one non-stale proposal and advance the shared project revision."""
    updated = deepcopy(payload)
    state = project_state_from_payload(updated)
    proposal = _proposal_by_id(state, proposal_id)
    if proposal.get("status") != "PENDING":
        raise ValueError(f"Proposal {proposal_id} is not pending")
    if int(proposal.get("base_revision", -1)) != int(state["revision"]):
        raise ValueError(
            f"Proposal {proposal_id} is stale: project revision changed after it was created"
        )

    applied = apply_proposal_operations(updated, proposal["operations"])
    # apply_proposal_operations copied the pre-application project_state, so overwrite it
    # with the authoritative proposal state before advancing the revision.
    state["revision"] += 1
    proposal["status"] = "APPLIED"
    proposal["applied_revision"] = state["revision"]
    applied["project_state"] = state
    return applied


def reject_board_proposal(payload: dict, proposal_id: str) -> dict:
    updated = deepcopy(payload)
    state = project_state_from_payload(updated)
    proposal = _proposal_by_id(state, proposal_id)
    if proposal.get("status") != "PENDING":
        raise ValueError(f"Proposal {proposal_id} is not pending")
    proposal["status"] = "REJECTED"
    updated["project_state"] = state
    return updated


def pending_board_proposals(payload: dict) -> tuple[dict, ...]:
    state = project_state_from_payload(payload)
    return tuple(
        deepcopy(item) for item in state["proposals"] if item.get("status") == "PENDING"
    )


def proposal_change_summary(proposal: dict) -> tuple[str, ...]:
    """Return compact human-readable operation summaries for UI/review surfaces."""
    rows: list[str] = []
    for operation in proposal.get("operations", []):
        kind = operation.get("kind")
        if kind == "ADD_BRANCH":
            identity = operation.get("values", {}).get(
                "circuit_id",
                operation.get("values", {}).get(
                    "field_id",
                    operation.get("values", {}).get("sub_board_id", operation.get("branch_kind")),
                ),
            )
            rows.append(f"+ Add {identity} below {operation.get('parent_uid', 'root')}")
        elif kind == "UPDATE_BRANCH":
            rows.append(
                f"~ Update {operation.get('target_uid')} · "
                + ", ".join(sorted(operation.get("values", {})))
            )
        elif kind == "MOVE_BRANCH":
            rows.append(
                f"→ Move {operation.get('target_uid')} below {operation.get('new_parent_uid')}"
            )
        elif kind == "REMOVE_BRANCH":
            rows.append(f"− Remove {operation.get('target_uid')} and downstream branches")
        elif kind == "UPDATE_BOARD":
            rows.append("~ Update board · " + ", ".join(sorted(operation.get("values", {}))))
    return tuple(rows)
