"""OpenAI-backed conversational adapter for the safe Planner Bridge.

The electrical Planner remains authoritative. The model receives only provider-neutral
Planner tools and cannot directly edit persistence. Live-board apply/reject actions are
intentionally withheld from the model so the engineer remains the approval boundary.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from .planner_bridge import get_project
from .planner_tool_contract import execute_planner_tool, planner_tool_definitions

_DEFAULT_MODEL = "gpt-5.6-terra"
_MODEL_ENV = "OPENAI_PLANNER_MODEL"
_REASONING_ENV = "OPENAI_PLANNER_REASONING"
_MAX_TOOL_ROUNDS = 10

_MODEL_TOOL_NAMES = {
    "get_project",
    "record_fact",
    "add_question",
    "resolve_question",
    "create_board_proposal",
    "preview_board_proposal",
}

_SYSTEM_INSTRUCTIONS = """You are the AI Board Assistant inside Kfir's personal electrical
Board Planner. You and Kfir collaborate on preliminary LV distribution-board design.

Core operating rules:
- Treat the current Planner project as the source of truth, not earlier chat wording.
- The user is the engineer/reviewer. Be concise, practical and collaborative.
- Distinguish USER_PROVIDED facts, DOCUMENT_EXTRACTED facts, DERIVED values and explicit
  ASSUMPTION values. Never disguise an assumption as a confirmed fact.
- Ask only questions that materially improve the next design step. Use BLOCKING only when
  the design cannot responsibly continue without the answer; otherwise NEEDED_SOON or DEFERRED.
- You may create and preview board proposals, but you may NOT apply or reject them. Kfir
  approves/rejects proposals in Board Planner.
- Propose structural/design inputs; let the Planner backend calculate design current,
  breaker candidates, cable candidates, phase allocation and design-review results.
- Never invent IEC requirements, manufacturer data, fault levels, selectivity, trip curves,
  protection settings or compliance conclusions.
- A breaker candidate is load-sized planning only. Cable/protection/selectivity verification
  remain separate unless the Planner explicitly reports a verified result.
- Prefer progress with clearly labelled assumptions when safe, rather than asking a long
  questionnaire before producing anything.
- When a user supplies a fact that affects the project, record it before relying on it.
- When enough information exists for a useful board change, create a proposal and tell the
  user what you proposed, important assumptions, and what still needs input.
"""


@dataclass(frozen=True)
class AssistantTurnResult:
    text: str
    response_id: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_calls: tuple[str, ...] = tuple()


def api_key_configured(environment: dict[str, str] | None = None) -> bool:
    env = os.environ if environment is None else environment
    return bool(str(env.get("OPENAI_API_KEY", "")).strip())


def configured_model(environment: dict[str, str] | None = None) -> str:
    env = os.environ if environment is None else environment
    return str(env.get(_MODEL_ENV, _DEFAULT_MODEL)).strip() or _DEFAULT_MODEL


def configured_reasoning(environment: dict[str, str] | None = None) -> str:
    env = os.environ if environment is None else environment
    value = str(env.get(_REASONING_ENV, "low")).strip().lower()
    return value if value in {"none", "low", "medium", "high", "xhigh", "max"} else "low"


def _openai_tools() -> list[dict]:
    tools: list[dict] = []
    for definition in planner_tool_definitions():
        if definition["name"] not in _MODEL_TOOL_NAMES:
            continue
        tools.append(
            {
                "type": "function",
                "name": definition["name"],
                "description": definition["description"],
                "parameters": definition["parameters"],
            }
        )
    return tools


def _response_output(response) -> list[Any]:
    output = getattr(response, "output", None)
    return list(output or [])


def _function_calls(response) -> list[Any]:
    return [item for item in _response_output(response) if getattr(item, "type", None) == "function_call"]


def _usage_tokens(response) -> tuple[int | None, int | None]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None, None
    return getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None)


def _response_text(response) -> str:
    direct = getattr(response, "output_text", None)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    chunks: list[str] = []
    for item in _response_output(response):
        if getattr(item, "type", None) != "message":
            continue
        for content in list(getattr(item, "content", None) or []):
            if getattr(content, "type", None) == "output_text":
                text = getattr(content, "text", None)
                if isinstance(text, str) and text.strip():
                    chunks.append(text.strip())
    return "\n\n".join(chunks).strip()


def _safe_tool_result(name: str, arguments: dict, *, path: Path | None = None) -> dict:
    if name not in _MODEL_TOOL_NAMES:
        return {"ok": False, "error": f"Tool {name!r} is not available to the model."}
    try:
        result = execute_planner_tool(name, arguments, path=path)
    except (OSError, TypeError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "result": result}


def _current_project_context(*, path: Path | None = None) -> str:
    snapshot = get_project(path=path)
    return json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))


def _create_response(client, *, input_value, previous_response_id: str | None):
    kwargs = {
        "model": configured_model(),
        "instructions": _SYSTEM_INSTRUCTIONS,
        "input": input_value,
        "tools": _openai_tools(),
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "reasoning": {"effort": configured_reasoning()},
        "max_output_tokens": 3000,
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id
    return client.responses.create(**kwargs)


def run_assistant_turn(
    user_message: str,
    *,
    previous_response_id: str | None = None,
    client=None,
    path: Path | None = None,
) -> AssistantTurnResult:
    """Run one conversational turn, including any Planner tool-call round trips."""
    message = str(user_message).strip()
    if not message:
        raise ValueError("user_message is required")

    if client is None:
        if not api_key_configured():
            raise RuntimeError("OPENAI_API_KEY is not configured")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The OpenAI Python package is not installed") from exc
        client = OpenAI()

    current_context = _current_project_context(path=path)
    first_input = (
        "CURRENT PLANNER PROJECT SNAPSHOT (authoritative at start of this turn):\n"
        + current_context
        + "\n\nUSER MESSAGE:\n"
        + message
    )
    response = _create_response(
        client,
        input_value=first_input,
        previous_response_id=previous_response_id,
    )

    called: list[str] = []
    total_input = 0
    total_output = 0
    saw_usage = False

    for _ in range(_MAX_TOOL_ROUNDS + 1):
        input_tokens, output_tokens = _usage_tokens(response)
        if input_tokens is not None:
            total_input += int(input_tokens)
            saw_usage = True
        if output_tokens is not None:
            total_output += int(output_tokens)
            saw_usage = True

        calls = _function_calls(response)
        if not calls:
            text = _response_text(response)
            if not text:
                raise RuntimeError("The model returned no assistant text.")
            return AssistantTurnResult(
                text=text,
                response_id=str(getattr(response, "id")),
                input_tokens=total_input if saw_usage else None,
                output_tokens=total_output if saw_usage else None,
                tool_calls=tuple(called),
            )

        tool_outputs = []
        for call in calls:
            name = str(getattr(call, "name", ""))
            called.append(name)
            try:
                arguments = json.loads(str(getattr(call, "arguments", "") or "{}"))
            except json.JSONDecodeError:
                result = {"ok": False, "error": "Tool arguments were not valid JSON."}
            else:
                if not isinstance(arguments, dict):
                    result = {"ok": False, "error": "Tool arguments must decode to an object."}
                else:
                    result = _safe_tool_result(name, arguments, path=path)
            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": str(getattr(call, "call_id")),
                    "output": json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                }
            )

        response = _create_response(
            client,
            input_value=tool_outputs,
            previous_response_id=str(getattr(response, "id")),
        )

    raise RuntimeError("The assistant exceeded the maximum Planner tool-call rounds.")
