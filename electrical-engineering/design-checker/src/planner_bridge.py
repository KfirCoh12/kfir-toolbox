"""Persistence-aware bridge for future AI clients.

This module is intentionally model/provider agnostic. It is the boundary an embedded
assistant or future MCP adapter can call. Every write goes through project-state or
proposal validation; no AI client needs direct access to the Board Planner JSON file.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .board_persistence import load_last_board, save_last_board
from .board_planner_state import planner_owned_payload
from .design_review import design_review_summary
from .planner_proposals import (
    apply_board_proposal,
    create_board_proposal,
    pending_board_proposals,
    preview_board_proposal,
    proposal_change_summary,
    reject_board_proposal,
)
from .project_state import (
    add_project_question,
    open_project_questions,
    project_state_from_payload,
    record_project_fact,
    resolve_project_question,
)
from .working_board_plan import calculate_working_board


PLANNER_BRIDGE_TOOL_NAMES = (
    "get_project",
    "record_fact",
    "add_question",
    "resolve_question",
    "create_board_proposal",
    "preview_board_proposal",
    "apply_board_proposal",
    "reject_board_proposal",
)


def _load_required(path: Path | None = None) -> dict:
    payload = load_last_board(path)
    if payload is None:
        raise ValueError("No working board exists yet")
    return payload


def _save_project_state(payload: dict, path: Path | None = None) -> None:
    save_last_board({"project_state": deepcopy(payload["project_state"])}, path)


def _save_board_and_project(payload: dict, path: Path | None = None) -> None:
    update = planner_owned_payload(payload)
    update["project_state"] = deepcopy(payload["project_state"])
    save_last_board(update, path)


def _review_snapshot(payload: dict) -> dict:
    finals = [
        item
        for item in payload.get("branches", [])
        if isinstance(item, dict) and item.get("kind") == "final"
    ]
    if not finals:
        return {
            "calculated": False,
            "attention_count": 0,
            "limitation_count": 0,
            "groups": [],
        }

    calculated = calculate_working_board(payload)
    review = design_review_summary(calculated)
    root_plan = calculated.hierarchy.root.plan
    groups = [
        {
            "code": group.code,
            "severity": group.severity,
            "scope": group.scope,
            "title": group.title,
            "detail": group.detail,
            "target_ids": list(group.target_ids),
        }
        for group in review.groups
    ]
    return {
        "calculated": True,
        "max_phase_current_a": (
            root_plan.phase_balance.max_phase_current_a if root_plan is not None else None
        ),
        "incomer_candidate_a": (
            root_plan.incomer_candidate.breaker_rating_a if root_plan is not None else None
        ),
        "attention_count": review.attention_count,
        "limitation_count": review.limitation_count,
        "groups": groups,
    }


def project_snapshot(payload: dict) -> dict:
    """Return the compact state intended for an AI/client instead of raw persistence."""
    state = project_state_from_payload(payload)
    board = planner_owned_payload(payload)
    pending = pending_board_proposals(payload)
    return {
        "revision": state["revision"],
        "board": board,
        "facts": deepcopy(state["facts"]),
        "open_questions": [deepcopy(item) for item in open_project_questions(payload)],
        "pending_proposals": [
            {
                "proposal_id": item["proposal_id"],
                "base_revision": item["base_revision"],
                "title": item["title"],
                "reason": item["reason"],
                "assumptions": deepcopy(item.get("assumptions", [])),
                "changes": list(proposal_change_summary(item)),
            }
            for item in pending
        ],
        "engineering_context": {
            key: deepcopy(payload[key])
            for key in ("fault_source", "fault_network")
            if key in payload
        },
        "review": _review_snapshot(payload),
    }


def get_project(*, path: Path | None = None) -> dict:
    return project_snapshot(_load_required(path))


def record_fact(
    *,
    key: str,
    value,
    provenance: str,
    source_ref: str | None = None,
    note: str | None = None,
    path: Path | None = None,
) -> dict:
    payload = _load_required(path)
    updated = record_project_fact(
        payload,
        key=key,
        value=value,
        provenance=provenance,
        source_ref=source_ref,
        note=note,
    )
    _save_project_state(updated, path)
    return project_snapshot(updated)


def add_question(
    *,
    prompt: str,
    priority: str,
    related_keys: tuple[str, ...] = tuple(),
    path: Path | None = None,
) -> dict:
    payload = _load_required(path)
    updated, question_id = add_project_question(
        payload,
        prompt=prompt,
        priority=priority,
        related_keys=related_keys,
    )
    _save_project_state(updated, path)
    result = project_snapshot(updated)
    result["created_question_id"] = question_id
    return result


def resolve_question(
    *,
    question_id: str,
    answer: str | None = None,
    status: str = "ANSWERED",
    path: Path | None = None,
) -> dict:
    payload = _load_required(path)
    updated = resolve_project_question(
        payload,
        question_id=question_id,
        answer=answer,
        status=status,
    )
    _save_project_state(updated, path)
    return project_snapshot(updated)


def create_proposal(
    *,
    title: str,
    reason: str,
    operations,
    assumptions: tuple[str, ...] = tuple(),
    path: Path | None = None,
) -> dict:
    payload = _load_required(path)
    updated, proposal_id = create_board_proposal(
        payload,
        title=title,
        reason=reason,
        operations=operations,
        assumptions=assumptions,
    )
    _save_project_state(updated, path)
    result = project_snapshot(updated)
    result["created_proposal_id"] = proposal_id
    return result


def preview_proposal(*, proposal_id: str, path: Path | None = None) -> dict:
    payload = _load_required(path)
    board, calculated, review = preview_board_proposal(payload, proposal_id)
    if calculated is None or review is None:
        result = {
            "proposal_id": proposal_id,
            "board": planner_owned_payload(board),
            "review": {
                "calculated": False,
                "attention_count": 0,
                "limitation_count": 0,
                "groups": [],
            },
        }
    else:
        result = {
            "proposal_id": proposal_id,
            "board": planner_owned_payload(board),
            "review": _review_snapshot(board),
        }
    return result


def apply_proposal(*, proposal_id: str, path: Path | None = None) -> dict:
    payload = _load_required(path)
    updated = apply_board_proposal(payload, proposal_id)
    _save_board_and_project(updated, path)
    return project_snapshot(updated)


def reject_proposal(*, proposal_id: str, path: Path | None = None) -> dict:
    payload = _load_required(path)
    updated = reject_board_proposal(payload, proposal_id)
    _save_project_state(updated, path)
    return project_snapshot(updated)
