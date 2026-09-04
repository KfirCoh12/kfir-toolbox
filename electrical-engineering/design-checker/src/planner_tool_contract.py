"""Provider-neutral tool contract for the future Board Planner assistant.

The definitions are ordinary JSON-schema-shaped dictionaries, intentionally not tied
to one model SDK. A later OpenAI adapter can wrap these definitions without changing
the Planner Bridge or its safety boundary.
"""
from __future__ import annotations

from pathlib import Path

from .planner_bridge import (
    PLANNER_BRIDGE_TOOL_NAMES,
    add_question,
    apply_proposal,
    create_proposal,
    get_project,
    preview_proposal,
    record_fact,
    reject_proposal,
    resolve_question,
)


_OPERATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["kind"],
    "properties": {
        "kind": {
            "type": "string",
            "enum": [
                "ADD_BRANCH",
                "UPDATE_BRANCH",
                "MOVE_BRANCH",
                "REMOVE_BRANCH",
                "UPDATE_BOARD",
            ],
        },
        "ref": {"type": "string"},
        "branch_kind": {
            "type": "string",
            "enum": ["circuit", "field", "sub_board"],
        },
        "parent_uid": {"type": "string"},
        "target_uid": {"type": "string"},
        "new_parent_uid": {"type": "string"},
        "values": {"type": "object"},
    },
}


PLANNER_TOOL_DEFINITIONS = (
    {
        "name": "get_project",
        "description": (
            "Read the current Board Planner project: revision, structural board, known "
            "facts, open questions, pending proposals, engineering context and design review."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
    },
    {
        "name": "record_fact",
        "description": (
            "Record an explicit project fact, extracted fact, derivation or clearly marked "
            "assumption. Never use ASSUMPTION for something the user actually confirmed."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["key", "value", "provenance"],
            "properties": {
                "key": {"type": "string"},
                "value": {},
                "provenance": {
                    "type": "string",
                    "enum": [
                        "USER_PROVIDED",
                        "DOCUMENT_EXTRACTED",
                        "DERIVED",
                        "ASSUMPTION",
                        "CONFIRMED",
                    ],
                },
                "source_ref": {"type": ["string", "null"]},
                "note": {"type": ["string", "null"]},
            },
        },
    },
    {
        "name": "add_question",
        "description": (
            "Record a missing project question and its urgency. Use BLOCKING only when "
            "the current design cannot responsibly continue without the answer."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["prompt", "priority"],
            "properties": {
                "prompt": {"type": "string"},
                "priority": {
                    "type": "string",
                    "enum": ["BLOCKING", "NEEDED_SOON", "DEFERRED"],
                },
                "related_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
    },
    {
        "name": "resolve_question",
        "description": (
            "Mark a stored project question answered or dismissed. Record any resulting "
            "engineering fact separately with record_fact so provenance stays explicit."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["question_id"],
            "properties": {
                "question_id": {"type": "string"},
                "answer": {"type": ["string", "null"]},
                "status": {
                    "type": "string",
                    "enum": ["ANSWERED", "DISMISSED"],
                },
            },
        },
    },
    {
        "name": "create_board_proposal",
        "description": (
            "Create a non-destructive board-change proposal. The Planner validates hierarchy "
            "and recalculates the proposal before storing it. Use @ref values to make later "
            "operations target branches added earlier in the same proposal."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "reason", "operations"],
            "properties": {
                "title": {"type": "string"},
                "reason": {"type": "string"},
                "operations": {
                    "type": "array",
                    "minItems": 1,
                    "items": _OPERATION_SCHEMA,
                },
                "assumptions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
    },
    {
        "name": "preview_board_proposal",
        "description": (
            "Recalculate one pending non-stale proposal and return the proposed board and "
            "design-review result without changing the live board."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["proposal_id"],
            "properties": {"proposal_id": {"type": "string"}},
        },
    },
    {
        "name": "apply_board_proposal",
        "description": (
            "Apply a user-approved pending proposal. Stale proposals are rejected if the "
            "project revision changed since proposal creation."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["proposal_id"],
            "properties": {"proposal_id": {"type": "string"}},
        },
    },
    {
        "name": "reject_board_proposal",
        "description": "Reject a pending proposal without changing the live board.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["proposal_id"],
            "properties": {"proposal_id": {"type": "string"}},
        },
    },
)


def planner_tool_definitions() -> tuple[dict, ...]:
    return PLANNER_TOOL_DEFINITIONS


def execute_planner_tool(
    name: str,
    arguments: dict | None = None,
    *,
    path: Path | None = None,
) -> dict:
    """Execute one tool-call payload through the persistence-aware Planner Bridge."""
    args = dict(arguments or {})
    if name == "get_project":
        if args:
            raise ValueError("get_project does not accept arguments")
        return get_project(path=path)
    if name == "record_fact":
        return record_fact(path=path, **args)
    if name == "add_question":
        if "related_keys" in args:
            args["related_keys"] = tuple(args["related_keys"])
        return add_question(path=path, **args)
    if name == "resolve_question":
        return resolve_question(path=path, **args)
    if name == "create_board_proposal":
        if "assumptions" in args:
            args["assumptions"] = tuple(args["assumptions"])
        return create_proposal(path=path, **args)
    if name == "preview_board_proposal":
        return preview_proposal(path=path, **args)
    if name == "apply_board_proposal":
        return apply_proposal(path=path, **args)
    if name == "reject_board_proposal":
        return reject_proposal(path=path, **args)
    raise ValueError(f"Unknown Planner tool: {name}")


assert tuple(item["name"] for item in PLANNER_TOOL_DEFINITIONS) == PLANNER_BRIDGE_TOOL_NAMES
