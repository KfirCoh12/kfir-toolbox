"""High-fidelity workspace preview for the next-generation UI shell."""
import streamlit as st

from src.board_persistence import load_last_board
from src.protection_hierarchy import protection_relationships
from src.source_fault import FaultSourceDeclaration, calculate_root_busbar_fault
from src.ui_theme import apply_theme, page_header, section_header
from src.working_board_plan import calculate_working_board

st.set_page_config(
    page_title="Engineering Workspace",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()


def fmt_a(value):
    return "—" if value is None else f"{value:.1f} A"


def fmt_rating(value):
    return "—" if value is None else f"{value:g} A"


def fmt_cable(mm2, runs):
    if mm2 is None:
        return "—"
    count = runs or 1
    return f"{count} × {mm2:g} mm²" if count > 1 else f"{mm2:g} mm²"


def source_fault(saved, voltage_v):
    source = saved.get("fault_source")
    if not isinstance(source, dict):
        return None
    kind = str(source.get("kind", "NONE"))
    try:
        if kind == "DECLARED_BUSBAR" and source.get("prospective_fault_current_ka") is not None:
            return calculate_root_busbar_fault(
                FaultSourceDeclaration(
                    kind="DECLARED_BUSBAR",
                    prospective_fault_current_ka=float(source["prospective_fault_current_ka"]),
                    evidence_record_ref=str(source.get("evidence_record_ref", "")),
                    rule_basis_ref=str(source.get("rule_basis_ref", "")),
                )
            )
        if kind == "TRANSFORMER_TERMINAL" and source.get("transformer_rated_power_kva") is not None and source.get("transformer_impedance_percent") is not None:
            return calculate_root_busbar_fault(
                FaultSourceDeclaration(
                    kind="TRANSFORMER_TERMINAL",
                    transformer_rated_power_kva=float(source["transformer_rated_power_kva"]),
                    transformer_secondary_voltage_v=float(voltage_v),
                    transformer_impedance_percent=float(source["transformer_impedance_percent"]),
                    evidence_record_ref=str(source.get("evidence_record_ref", "")),
                    rule_basis_ref=str(source.get("rule_basis_ref", "")),
                )
            )
    except (TypeError, ValueError):
        return None
    return None


try:
    saved = load_last_board()
except ValueError as exc:
    saved = None
    st.error(str(exc))

if saved is None:
    page_header(
        eyebrow="Engineering workspace · UI preview",
        title="Project workspace",
        subtitle="A control-room style shell for designing, reviewing and verifying electrical distribution systems.",
        chips=(("UI concept", "accent"),),
    )
    st.info("Create a board in Board Planner first. This preview intentionally uses your real project data rather than demo content.")
    st.stop()

try:
    calculated = calculate_working_board(saved)
    graph = calculated.graph
    relationships = protection_relationships(graph)
except (TypeError, ValueError) as exc:
    st.error(f"Could not calculate the working board: {exc}")
    st.stop()

board_id = str(saved.get("board_id", "Board"))
description = str(saved.get("description", "Distribution board"))
contexts = calculated.context_by_circuit_id
root_plan = calculated.hierarchy.root.plan
fault_result = source_fault(saved, graph.line_to_line_voltage_v)

attention = []
if fault_result is None:
    attention.append("Main-board fault source not declared")
if relationships:
    attention.append("Breaking capacity evidence still required")
if any(item.cable_mm2 is None for item in contexts.values()):
    attention.append("One or more cable candidates unresolved")

page_header(
    eyebrow="Electrical engineering · Operations workspace",
    title=f"{board_id} · {description}",
    subtitle="Design, inspect and verify from one engineering workspace. The interface separates design context, unresolved engineering inputs and verification state so attention goes to what actually needs a decision.",
    chips=(("LIVE BOARD", "good"), (f"{len(contexts)} circuits", ""), (f"{len(attention)} attention", "warn" if attention else "good")),
)

# Workflow ribbon
workflow_cols = st.columns([1, 1, 1, 1.4], gap="small")
with workflow_cols[0]:
    with st.container(border=True):
        st.caption("01 · STRUCTURE")
        st.markdown("**Board topology**")
        st.caption("Configured")
with workflow_cols[1]:
    with st.container(border=True):
        st.caption("02 · DESIGN")
        st.markdown("**Load & sizing**")
        st.caption("Live calculation")
with workflow_cols[2]:
    with st.container(border=True):
        st.caption("03 · REVIEW")
        st.markdown("**Protection**")
        st.caption("Needs evidence" if relationships else "No pairs yet")
with workflow_cols[3]:
    with st.container(border=True):
        st.caption("PROJECT STATE")
        state = "Engineering review required" if attention else "No open review items"
        st.markdown(f"**{state}**")
        st.caption("The workspace should surface exceptions rather than make you hunt through forms.")

section_header("System overview", "High-value operating context stays visible before detailed editing begins.")
metrics = st.columns(5, gap="small")
max_phase = root_plan.phase_balance.max_phase_current_a if root_plan is not None else None
incomer = root_plan.incomer_candidate.breaker_rating_a if root_plan is not None else None
metrics[0].metric("System", f"{graph.line_to_line_voltage_v:g} / {graph.line_to_neutral_voltage_v:g} V")
metrics[1].metric("Max phase", fmt_a(max_phase))
metrics[2].metric("Incomer candidate", fmt_rating(incomer))
metrics[3].metric("Fault level", "—" if fault_result is None else f"{fault_result.prospective_fault_current_ka:.2f} kA")
metrics[4].metric("Protection pairs", str(len(relationships)))

main_left, main_right = st.columns([2.15, .85], gap="large")
with main_left:
    section_header("Distribution schedule", "One operational table: design context first, exceptions highlighted elsewhere.")
    rows = []
    for context in calculated.circuit_contexts:
        rows.append({
            "Circuit": context.circuit_id,
            "Ib": fmt_a(context.design_current_a),
            "Protection": fmt_rating(context.breaker_candidate_a),
            "Cable": fmt_cable(context.cable_mm2, context.cable_runs),
            "Design state": "Calculated" if context.breaker_candidate_a is not None and context.cable_mm2 is not None else "Needs input",
        })
    st.dataframe(rows, hide_index=True, use_container_width=True, height=min(440, 78 + max(1, len(rows)) * 35))

with main_right:
    section_header("Attention", "Only unresolved or decision-worthy items should compete for attention.")
    with st.container(border=True):
        if attention:
            for index, item in enumerate(attention, start=1):
                st.markdown(f"**{index:02d} · {item}**")
                if item.startswith("Main-board"):
                    st.caption("Protection Checks → Fault source")
                elif item.startswith("Breaking"):
                    st.caption("Protection Checks → Device evidence")
                else:
                    st.caption("Board Planner → Branch properties")
                if index != len(attention):
                    st.divider()
        else:
            st.success("No open engineering attention items in the current preview scope.")

section_header("Protection chain", "A relationship-centric review surface replaces repeated cards and raw internal IDs.")
if not relationships:
    st.info("No adjacent protective-device relationships are available yet.")
else:
    protection_rows = []
    for rel in relationships:
        upstream = graph.node_by_id.get(rel.upstream_node_id)
        downstream = graph.node_by_id.get(rel.downstream_node_id)
        protection_rows.append({
            "Circuit": rel.downstream_circuit_id or "—",
            "Upstream": upstream.label if upstream else rel.upstream_node_id,
            "Upstream A": fmt_rating(rel.upstream_rating_a),
            "Downstream": downstream.label if downstream else rel.downstream_node_id,
            "Downstream A": fmt_rating(rel.downstream_rating_a),
            "Breaking capacity": "Needs data",
            "Selectivity": "Not checked",
        })
    st.dataframe(protection_rows, hide_index=True, use_container_width=True)

section_header("UI direction", "This page is intentionally a visual/workflow prototype before we migrate editing controls.")
d1, d2, d3 = st.columns(3, gap="small")
with d1:
    with st.container(border=True):
        st.caption("INFORMATION HIERARCHY")
        st.markdown("**Less decorative text, more operating context**")
        st.caption("Project state → engineering summary → schedule → exceptions → detail.")
with d2:
    with st.container(border=True):
        st.caption("SEMANTIC COLOR")
        st.markdown("**Blue = active · green = resolved · amber = attention · red = failure**")
        st.caption("Color carries state, not decoration.")
with d3:
    with st.container(border=True):
        st.caption("WORKFLOW DENSITY")
        st.markdown("**Wide tables and compact controls**")
        st.caption("Use the screen like an engineering workstation, not a vertical questionnaire.")

st.caption("UI revamp preview · existing calculation and persistence engines remain unchanged.")
