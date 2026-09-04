"""Persistent project knowledge used by the future AI/Planner collaboration layer.

The electrical board remains the engineering source of truth. This module stores the
additional facts, assumptions and open questions needed to let an assistant reason
about an incomplete project without silently inventing missing information.

The state deliberately lives as one top-level key in the existing shared Board Planner
record so the current persistence layer can retain it beside protection/fault metadata.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Literal

FactProvenance = Literal[
    "USER_PROVIDED",
    "DOCUMENT_EXTRACTED",
    "DERIVED",
    "ASSUMPTION",
    "CONFIRMED",
]
QuestionPriority = Literal["BLOCKING", "NEEDED_SOON", "DEFERRED"]
QuestionStatus = Literal["OPEN", "ANSWERED", "DISMISSED"]

_FACT_PROVENANCE = {
    "USER_PROVIDED",
    "DOCUMENT_EXTRACTED",
    "DERIVED",
    "ASSUMPTION",
    "CONFIRMED",
}
_QUESTION_PRIORITIES = {"BLOCKING", "NEEDED_SOON", "DEFERRED"}
_QUESTION_STATUSES = {"OPEN", "ANSWERED", "DISMISSED"}


def default_project_state() -> dict:
    return {
        "revision": 0,
        "proposal_counter": 0,
        "question_counter": 0,
        "facts": {},
        "questions": [],
        "proposals": [],
    }


def _nonblank(value, label: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{label} is required")
    return text


def project_state_from_payload(payload: dict) -> dict:
    """Return a validated, detached project-state dictionary.

    Older saved boards have no project_state key. They are treated as revision zero
    rather than migrated destructively on read.
    """
    raw = payload.get("project_state")
    if raw is None:
        return default_project_state()
    if not isinstance(raw, dict):
        raise ValueError("project_state must be an object")

    state = default_project_state()
    state.update(deepcopy(raw))

    for key in ("revision", "proposal_counter", "question_counter"):
        value = state.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"project_state.{key} must be a non-negative integer")

    facts = state.get("facts")
    if not isinstance(facts, dict):
        raise ValueError("project_state.facts must be an object")
    for fact_key, fact in facts.items():
        _nonblank(fact_key, "fact key")
        if not isinstance(fact, dict):
            raise ValueError(f"project fact {fact_key!r} must be an object")
        provenance = str(fact.get("provenance", ""))
        if provenance not in _FACT_PROVENANCE:
            raise ValueError(f"project fact {fact_key!r} has unsupported provenance")

    questions = state.get("questions")
    if not isinstance(questions, list):
        raise ValueError("project_state.questions must be a list")
    for question in questions:
        if not isinstance(question, dict):
            raise ValueError("project questions must be objects")
        _nonblank(question.get("question_id"), "question_id")
        _nonblank(question.get("prompt"), "question prompt")
        if question.get("priority") not in _QUESTION_PRIORITIES:
            raise ValueError("project question has unsupported priority")
        if question.get("status") not in _QUESTION_STATUSES:
            raise ValueError("project question has unsupported status")

    proposals = state.get("proposals")
    if not isinstance(proposals, list):
        raise ValueError("project_state.proposals must be a list")
    if not all(isinstance(item, dict) for item in proposals):
        raise ValueError("project proposals must be objects")

    return state


def with_project_state(payload: dict, state: dict) -> dict:
    updated = deepcopy(payload)
    updated["project_state"] = project_state_from_payload({"project_state": state})
    return updated


def project_revision(payload: dict) -> int:
    return int(project_state_from_payload(payload)["revision"])


def bump_project_revision(payload: dict) -> dict:
    updated = deepcopy(payload)
    state = project_state_from_payload(updated)
    state["revision"] += 1
    updated["project_state"] = state
    return updated


def record_project_fact(
    payload: dict,
    *,
    key: str,
    value,
    provenance: FactProvenance,
    source_ref: str | None = None,
    note: str | None = None,
) -> dict:
    """Record one explicit project fact/assumption and advance the design revision."""
    fact_key = _nonblank(key, "fact key")
    if provenance not in _FACT_PROVENANCE:
        raise ValueError(f"Unsupported fact provenance: {provenance}")

    updated = deepcopy(payload)
    state = project_state_from_payload(updated)
    fact = {
        "value": deepcopy(value),
        "provenance": provenance,
    }
    if source_ref is not None and str(source_ref).strip():
        fact["source_ref"] = str(source_ref).strip()
    if note is not None and str(note).strip():
        fact["note"] = str(note).strip()
    state["facts"][fact_key] = fact
    state["revision"] += 1
    updated["project_state"] = state
    return updated


def add_project_question(
    payload: dict,
    *,
    prompt: str,
    priority: QuestionPriority,
    related_keys: tuple[str, ...] = tuple(),
) -> tuple[dict, str]:
    """Add an open question without changing the engineering revision."""
    text = _nonblank(prompt, "question prompt")
    if priority not in _QUESTION_PRIORITIES:
        raise ValueError(f"Unsupported question priority: {priority}")

    updated = deepcopy(payload)
    state = project_state_from_payload(updated)
    state["question_counter"] += 1
    question_id = f"Q-{state['question_counter']:03d}"
    state["questions"].append(
        {
            "question_id": question_id,
            "prompt": text,
            "priority": priority,
            "status": "OPEN",
            "related_keys": [str(key).strip() for key in related_keys if str(key).strip()],
        }
    )
    updated["project_state"] = state
    return updated, question_id


def resolve_project_question(
    payload: dict,
    *,
    question_id: str,
    answer: str | None = None,
    status: Literal["ANSWERED", "DISMISSED"] = "ANSWERED",
) -> dict:
    """Close one question. Recording any engineering fact remains a separate action."""
    qid = _nonblank(question_id, "question_id")
    if status not in ("ANSWERED", "DISMISSED"):
        raise ValueError("question resolution status must be ANSWERED or DISMISSED")

    updated = deepcopy(payload)
    state = project_state_from_payload(updated)
    match = next((item for item in state["questions"] if item.get("question_id") == qid), None)
    if match is None:
        raise ValueError(f"Unknown project question: {qid}")
    match["status"] = status
    if answer is not None and str(answer).strip():
        match["answer"] = str(answer).strip()
    updated["project_state"] = state
    return updated


def open_project_questions(payload: dict) -> tuple[dict, ...]:
    state = project_state_from_payload(payload)
    priority_order = {"BLOCKING": 0, "NEEDED_SOON": 1, "DEFERRED": 2}
    items = [deepcopy(item) for item in state["questions"] if item.get("status") == "OPEN"]
    items.sort(key=lambda item: (priority_order[item["priority"]], item["question_id"]))
    return tuple(items)
