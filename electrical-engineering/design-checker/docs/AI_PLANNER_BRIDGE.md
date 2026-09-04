# AI Planner Bridge — pre-API architecture

This document describes the provider-neutral collaboration layer that exists before
any OpenAI API key is configured.

## Goal

The assistant should behave as a designer/orchestrator, while the existing Planner
remains responsible for engineering calculations and validation.

The safe loop is:

1. Read current project state.
2. Record explicit facts / assumptions with provenance.
3. Record missing questions with priority.
4. Create a non-destructive board proposal.
5. Recalculate and preview the proposal through the existing Planner engine.
6. Let the engineer apply or reject it.
7. Continue from the new project revision.

The assistant never edits the persisted JSON directly and never supplies calculated
breaker/cable results as authoritative board outputs.

## Persistent project state

The shared board record can now carry `project_state` beside the existing structural
board and Protection Checks metadata.

It contains:

- `revision` — advances when engineering facts or the live board change.
- `facts` — values with provenance such as USER_PROVIDED, DOCUMENT_EXTRACTED,
  DERIVED, ASSUMPTION or CONFIRMED.
- `questions` — BLOCKING, NEEDED_SOON or DEFERRED questions.
- `proposals` — pending/applied/rejected board-change proposals.

Older boards without this key load as revision zero.

## Proposal safety

A proposal can only use these operations:

- `ADD_BRANCH`
- `UPDATE_BRANCH`
- `MOVE_BRANCH`
- `REMOVE_BRANCH`
- `UPDATE_BOARD`

Branch writes are restricted to Planner-owned engineering input fields. Proposal-local
references such as `@gp` allow one proposal to create a field and then add circuits
below it without knowing generated internal UIDs in advance.

Before a proposal is stored, its detached preview must pass hierarchy validation and,
when it contains final circuits, the normal working-board calculation.

Each proposal stores the project revision it was based on. If the engineer edits the
board or a relevant project fact changes afterward, the old proposal becomes stale
and cannot be applied.

## Provider-neutral tool menu

`src/planner_tool_contract.py` exposes JSON-schema-shaped definitions for:

- `get_project`
- `record_fact`
- `add_question`
- `resolve_question`
- `create_board_proposal`
- `preview_board_proposal`
- `apply_board_proposal`
- `reject_board_proposal`

`execute_planner_tool(...)` is the single dispatcher a future model adapter can call.

## Board Planner UI

When collaboration data exists, Board Planner now shows:

- Project context: known/assumed facts and open questions.
- Pending proposals: reason, change list and assumptions.
- Recalculated proposal preview.
- Apply / Reject controls.
- Project revision.

These panels stay out of the way when no collaboration state exists.

## What remains for the API step

No model SDK or external API is imported yet.

The remaining integration is intentionally thin:

1. configure the private API key in Railway;
2. add an embedded chat surface;
3. send the model the tool definitions from `planner_tool_contract.py`;
4. dispatch model tool calls through `execute_planner_tool`;
5. return tool results to the model;
6. keep final proposal approval in Board Planner.

Engineering rules and persistence do not need to be rewritten for that step.
