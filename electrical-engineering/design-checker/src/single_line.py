"""Structured single-line-diagram model generated from a board plan.

This module intentionally contains no drawing-library or Streamlit logic. It converts
an engineering BoardPlanResult into a renderer-neutral electrical hierarchy so SVG,
PDF, DXF, or other views can later consume the same source model.
"""
from dataclasses import dataclass
from typing import Literal

from .board_planner import BoardPlanResult, SchedulePhase

SLDNodeKind = Literal["source", "incomer", "busbar", "outgoing_device", "cable", "load"]
SLDScopeStatus = Literal["SUPPORTED_SCOPE", "PARTIAL_SCOPE", "NOT_VERIFIED"]


@dataclass(frozen=True)
class SLDNode:
    node_id: str
    kind: SLDNodeKind
    label: str
    parent_id: str | None
    circuit_id: str | None = None
    rating_a: float | None = None
    phase: SchedulePhase | None = None
    cable_mm2: float | None = None
    cable_runs: int | None = None
    scope_status: SLDScopeStatus = "SUPPORTED_SCOPE"
    issue_codes: tuple[str, ...] = tuple()


@dataclass(frozen=True)
class SingleLineDiagram:
    board_id: str
    description: str
    line_to_line_voltage_v: float
    line_to_neutral_voltage_v: float
    nodes: tuple[SLDNode, ...]

    @property
    def outgoing_count(self) -> int:
        return sum(node.kind == "outgoing_device" for node in self.nodes)

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(node.node_id for node in self.nodes)


def build_single_line_diagram(plan: BoardPlanResult) -> SingleLineDiagram:
    """Create a deterministic renderer-neutral SLD hierarchy from a board plan.

    The current board engine does not yet select protective-device families or verify
    board protection/selectivity, so the SLD deliberately labels devices generically.
    Missing cable selections remain explicit rather than being invented for drawing.
    """
    board_id = plan.request.board_id.strip()
    source_id = f"{board_id}:source"
    incomer_id = f"{board_id}:incomer"
    busbar_id = f"{board_id}:busbar"

    incomer = plan.incomer_candidate
    incomer_label = (
        f"Provisional incomer {incomer.breaker_rating_a:g} A"
        if incomer.breaker_rating_a is not None
        else "Incomer rating not available"
    )
    incomer_status: SLDScopeStatus = (
        "PARTIAL_SCOPE" if incomer.status == "CANDIDATE" else "NOT_VERIFIED"
    )
    incomer_issues = (
        ("board_incomer_protection_not_verified",)
        if incomer.status == "CANDIDATE"
        else ("board_incomer_candidate_unavailable",)
    )

    nodes: list[SLDNode] = [
        SLDNode(
            node_id=source_id,
            kind="source",
            label=(
                f"Supply {plan.request.line_to_line_voltage_v:g}/"
                f"{plan.request.line_to_neutral_voltage_v:g} V"
            ),
            parent_id=None,
        ),
        SLDNode(
            node_id=incomer_id,
            kind="incomer",
            label=incomer_label,
            parent_id=source_id,
            rating_a=incomer.breaker_rating_a,
            phase="3P",
            scope_status=incomer_status,
            issue_codes=incomer_issues,
        ),
        SLDNode(
            node_id=busbar_id,
            kind="busbar",
            label="Board busbar · rating not yet selected",
            parent_id=incomer_id,
            scope_status="PARTIAL_SCOPE",
            issue_codes=("board_busbar_rating_not_selected",),
        ),
    ]

    for row in plan.schedule_rows:
        base = f"{board_id}:{row.circuit_id}"
        device_id = f"{base}:device"
        cable_id = f"{base}:cable"
        load_id = f"{base}:load"
        issue_codes = row.blocking_issue_codes

        device_label = (
            f"Outgoing protection {row.breaker_a:g} A"
            if row.breaker_a is not None
            else "Outgoing protection not selected"
        )
        nodes.append(SLDNode(
            node_id=device_id,
            kind="outgoing_device",
            label=device_label,
            parent_id=busbar_id,
            circuit_id=row.circuit_id,
            rating_a=row.breaker_a,
            phase=row.assigned_phase,
            scope_status=row.scope_status,
            issue_codes=issue_codes,
        ))

        cable_label = (
            f"{row.cable_runs or 1} × {row.cable_mm2:g} mm² {row.material.title()}"
            if row.cable_mm2 is not None
            else "Cable sizing not verified"
        )
        nodes.append(SLDNode(
            node_id=cable_id,
            kind="cable",
            label=cable_label,
            parent_id=device_id,
            circuit_id=row.circuit_id,
            phase=row.assigned_phase,
            cable_mm2=row.cable_mm2,
            cable_runs=row.cable_runs,
            scope_status=row.scope_status,
            issue_codes=issue_codes,
        ))
        nodes.append(SLDNode(
            node_id=load_id,
            kind="load",
            label=row.description,
            parent_id=cable_id,
            circuit_id=row.circuit_id,
            phase=row.assigned_phase,
            scope_status=row.scope_status,
            issue_codes=issue_codes,
        ))

    return SingleLineDiagram(
        board_id=board_id,
        description=plan.request.description.strip(),
        line_to_line_voltage_v=plan.request.line_to_line_voltage_v,
        line_to_neutral_voltage_v=plan.request.line_to_neutral_voltage_v,
        nodes=tuple(nodes),
    )
