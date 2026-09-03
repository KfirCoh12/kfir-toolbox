"""Wide-layout HMI Board Planner preview.

This presentation-only workspace keeps hierarchy, schedule and properties together
above a full-width adaptive single-line diagram. It deliberately reuses the existing
working-board calculation and editor helpers so the UI does not create a second
engineering model.
"""
from __future__ import annotations

from copy import deepcopy
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from .board_persistence import load_last_board
from .hmi_planner_workspace import (
    _CSS,
    _add_branch,
    _allowed_additions,
    _branch_label,
    _ensure_state,
    _fmt_a,
    _fmt_cable,
    _fmt_rating,
    _panel_header,
    _route_graph_nodes,
    _selected_branch,
)
from .hmi_single_line import render_hmi_single_line_svg
from .ui_theme import apply_theme
from .working_board_plan import calculate_working_board

_LAYOUT_CSS = r"""
<style>
.bp-tree-note{font-size:.63rem;color:#718aa7;margin:.1rem 0 .45rem}
[data-testid="stExpander"]{border-color:#203650!important;background:#091727!important}
[data-testid="stExpander"] summary p{font-size:.68rem!important;font-weight:650!important;color:#c9ddf3!important}
.bp-schedule-help{font-size:.62rem;color:#6f86a3;margin:-.2rem 0 .35rem}
.bp-diagram-head{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin:1rem 0 .45rem;padding:.55rem .7rem;border:1px solid #213a57;border-radius:8px;background:linear-gradient(90deg,rgba(14,31,51,.98),rgba(9,23,39,.96))}
.bp-diagram-title{font-size:.78rem;font-weight:760;color:#edf6ff;text-transform:uppercase;letter-spacing:.02em}.bp-diagram-sub{font-size:.64rem;color:#718aa7;margin-top:.08rem}.bp-diagram-mode{font-size:.61rem;color:#8fd1ff;border:1px solid rgba(54,167,255,.3);background:rgba(54,167,255,.07);border-radius:5px;padding:.22rem .45rem}
</style>
"""


def _descendants(branches: list[dict], parent_uid: str) -> list[dict]:
    return [item for item in branches if str(item.get("parent_key", "root")) == parent_uid]


def _select(uid: str) -> None:
    st.session_state["hmi_selected_uid"] = uid
    st.session_state["hmi_focus_circuit_id"] = None
    st.rerun()


def _hierarchy_item(branch: dict, branches: list[dict]) -> None:
    uid = str(branch.get("uid"))
    kind = str(branch.get("kind", "final"))
    children = _descendants(branches, uid)
    selected = uid == st.session_state.get("hmi_selected_uid", "root")
    label = _branch_label(branch).strip()
    if children:
        icon = "◇" if kind == "field" else "▣"
        identity = branch.get("field_id") if kind == "field" else branch.get("sub_board_id")
        with st.expander(f"{icon} {identity or label} · {len(children)} downstream", expanded=selected):
            if st.button(f"Select · {label}", key=f"tree_select_{uid}", use_container_width=True, type="primary" if selected else "secondary"):
                _select(uid)
            for child in children:
                _hierarchy_item(child, branches)
    elif st.button(label, key=f"tree_select_{uid}", use_container_width=True, type="primary" if selected else "secondary"):
        _select(uid)


def _render_hierarchy(board_id: str, branches: list[dict]) -> None:
    _panel_header("Hierarchy", "Collapse groups and select equipment to edit.", "NAVIGATION")
    selected_root = st.session_state.get("hmi_selected_uid", "root") == "root"
    if st.button(f"▰ {board_id} · Main board", key="tree_select_root", use_container_width=True, type="primary" if selected_root else "secondary"):
        _select("root")
    st.markdown('<div class="bp-tree-note">Fields and sub-boards expand only when you need their circuits.</div>', unsafe_allow_html=True)
    for branch in _descendants(branches, "root"):
        _hierarchy_item(branch, branches)


def _render_schedule(calculated) -> None:
    _panel_header("Circuit schedule", "Select one row to trace its complete electrical route.", "LIVE")
    schedule = []
    if calculated is not None:
        for context in calculated.circuit_contexts:
            schedule.append({"Circuit": context.circuit_id, "Ib": _fmt_a(context.design_current_a), "Breaker": _fmt_rating(context.breaker_candidate_a), "Cable": _fmt_cable(context.cable_mm2, context.cable_runs)})
    st.markdown('<div class="bp-schedule-help">The table remains the fast way to locate a circuit on large boards.</div>', unsafe_allow_html=True)
    event = st.dataframe(schedule, use_container_width=True, hide_index=True, height=310, on_select="rerun", selection_mode="single-row", key="hmi_schedule_select_v2")
    rows = []
    try:
        rows = list(event.selection.rows)
    except (AttributeError, TypeError):
        if isinstance(event, dict):
            rows = list(event.get("selection", {}).get("rows", []))
    if rows and 0 <= rows[0] < len(schedule):
        clicked = str(schedule[rows[0]]["Circuit"])
        if clicked != st.session_state.get("hmi_focus_circuit_id"):
            st.session_state["hmi_focus_circuit_id"] = clicked
            st.rerun()


def _render_properties(sandbox: dict, branches: list[dict], calculated, board_id: str, description: str) -> None:
    selected = _selected_branch(sandbox)
    if selected is None:
        _panel_header("Board properties", "Selected main-board context.", "INSPECTOR")
        bid = st.text_input("Board ID", value=board_id, key="hmi4_board_id")
        desc = st.text_input("Description", value=description, key="hmi4_board_desc")
        v1, v2 = st.columns(2)
        with v1:
            vll = st.number_input("L-L voltage (V)", min_value=1.0, value=float(sandbox.get("line_to_line_voltage_v", 400)), step=10.0, key="hmi4_vll")
        with v2:
            vln = st.number_input("L-N voltage (V)", min_value=1.0, value=float(sandbox.get("line_to_neutral_voltage_v", 230)), step=10.0, key="hmi4_vln")
        if st.button("Apply board changes", use_container_width=True, type="primary", key="hmi4_apply_board"):
            sandbox.update({"board_id": bid.strip() or board_id, "description": desc.strip() or description, "line_to_line_voltage_v": float(vll), "line_to_neutral_voltage_v": float(vln)})
            st.rerun()
        return
    kind = str(selected.get("kind", "item"))
    uid = str(selected.get("uid"))
    _panel_header("Properties", "Selected equipment and live design inputs.", kind.replace("_", " ").upper())
    if kind == "final":
        cid = st.text_input("Circuit ID", value=str(selected.get("circuit_id", "")), key=f"hmi4_cid_{uid}")
        desc = st.text_input("Description", value=str(selected.get("description", "")), key=f"hmi4_desc_{uid}")
        load = st.number_input("Connected load (kW)", min_value=.1, value=float(selected.get("load_kw", 5)), step=1.0, key=f"hmi4_load_{uid}")
        a, b = st.columns(2)
        with a:
            phase = st.selectbox("Phase", ["single", "three"], index=0 if selected.get("phase") == "single" else 1, format_func=lambda x: "1P" if x == "single" else "3P", key=f"hmi4_phase_{uid}")
        with b:
            material = st.selectbox("Conductor", ["copper", "aluminium"], index=1 if selected.get("material") == "aluminium" else 0, format_func=lambda x: "Aluminium" if x == "aluminium" else "Copper", key=f"hmi4_mat_{uid}")
        pf = st.number_input("Power factor", min_value=.01, max_value=1.0, value=float(selected.get("power_factor", .9)), step=.01, key=f"hmi4_pf_{uid}")
        demand = st.number_input("Demand factor", min_value=.01, max_value=1.0, value=float(selected.get("demand_factor", 1)), step=.05, key=f"hmi4_df_{uid}")
        if st.button("Apply circuit changes", use_container_width=True, type="primary", key=f"hmi4_apply_{uid}"):
            selected.update({"circuit_id": cid.strip() or selected.get("circuit_id"), "description": desc, "load_kw": float(load), "phase": phase, "material": material, "power_factor": float(pf), "demand_factor": float(demand)})
            st.rerun()
        if calculated is not None:
            context = calculated.context_by_circuit_id.get(str(selected.get("circuit_id", "")))
            if context is not None:
                st.caption(f"Live: Ib {_fmt_a(context.design_current_a)} · breaker {_fmt_rating(context.breaker_candidate_a)} · cable {_fmt_cable(context.cable_mm2, context.cable_runs)}")
    elif kind == "field":
        feeder = st.text_input("Feeder ID", value=str(selected.get("feeder_id", "")), key=f"hmi4_feed_{uid}")
        fid = st.text_input("Field ID", value=str(selected.get("field_id", "")), key=f"hmi4_field_{uid}")
        desc = st.text_input("Description", value=str(selected.get("description", "")), key=f"hmi4_fdesc_{uid}")
        material = st.selectbox("Feeder conductor", ["copper", "aluminium"], index=1 if selected.get("material") == "aluminium" else 0, key=f"hmi4_fmat_{uid}")
        if st.button("Apply field changes", use_container_width=True, type="primary", key=f"hmi4_apply_{uid}"):
            selected.update({"feeder_id": feeder.strip() or selected.get("feeder_id"), "field_id": fid.strip() or selected.get("field_id"), "description": desc, "material": material})
            st.rerun()
    else:
        feeder = st.text_input("Feeder ID", value=str(selected.get("feeder_id", "")), key=f"hmi4_sbfeed_{uid}")
        sid = st.text_input("Sub-board ID", value=str(selected.get("sub_board_id", "")), key=f"hmi4_sbid_{uid}")
        desc = st.text_input("Description", value=str(selected.get("description", "")), key=f"hmi4_sbdesc_{uid}")
        if st.button("Apply sub-board changes", use_container_width=True, type="primary", key=f"hmi4_apply_{uid}"):
            selected.update({"feeder_id": feeder.strip() or selected.get("feeder_id"), "sub_board_id": sid.strip() or selected.get("sub_board_id"), "description": desc})
            st.rerun()


def render_workspace() -> None:
    apply_theme()
    st.markdown(_CSS + _LAYOUT_CSS, unsafe_allow_html=True)
    try:
        persisted = load_last_board()
    except ValueError as exc:
        st.error(str(exc))
        return
    if persisted is None:
        st.info("Create a working board in Board Planner first.")
        return
    _ensure_state(persisted)
    sandbox = st.session_state["hmi_board_sandbox"]
    branches = sandbox.setdefault("branches", [])
    selected = _selected_branch(sandbox)
    focus_circuit_id = st.session_state.get("hmi_focus_circuit_id")
    try:
        calculated = calculate_working_board(sandbox)
        graph = calculated.graph
        root_plan = calculated.hierarchy.root.plan
        calculation_error = None
    except (TypeError, ValueError) as exc:
        calculated = None
        graph = None
        root_plan = None
        calculation_error = str(exc)
    board_id = str(sandbox.get("board_id", "Board"))
    description = str(sandbox.get("description", "Distribution board"))
    st.markdown(f'<div class="bp-topbar"><div class="bp-brand"><div class="bp-brand-mark">◈</div><div><div class="bp-kicker">Electrical distribution · design workstation</div><div class="bp-title">{escape(board_id)} · {escape(description)}</div></div></div><div class="bp-topmeta"><span class="bp-pill preview">HMI DESIGN PREVIEW</span><span class="bp-pill live">● LIVE CALCULATION</span><span class="bp-pill">{sandbox.get("line_to_line_voltage_v",400):g} V L-L</span><span class="bp-pill">{len(branches)} branches</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="bp-toolbar"><span class="bp-path">Project / Distribution / Board Planner / Working board</span><span class="bp-toolbar-note">Wide workbench preview</span></div>', unsafe_allow_html=True)
    allowed = _allowed_additions(selected)
    parent_key = "root" if selected is None else str(selected.get("uid"))
    context_name = "Main board" if selected is None else _branch_label(selected).strip()
    st.markdown(f'<div class="bp-contextbar"><strong>{"Add downstream of " + escape(context_name) if allowed else "Final circuit selected"}</strong><span>{"Only hierarchy-valid actions are shown" if allowed else "No downstream additions apply"}</span></div>', unsafe_allow_html=True)
    action_cols = st.columns([.8,.8,.9,.9,4.0], gap="small")
    if "circuit" in allowed:
        with action_cols[0]:
            if st.button("＋ Circuit", use_container_width=True, type="primary", key="hmi4_add_circuit"):
                _add_branch(sandbox, "circuit", parent_key)
    if "field" in allowed:
        with action_cols[1]:
            if st.button("＋ Field", use_container_width=True, key="hmi4_add_field"):
                _add_branch(sandbox, "field", parent_key)
    if "sub_board" in allowed:
        with action_cols[2]:
            if st.button("＋ Sub-board", use_container_width=True, key="hmi4_add_sub"):
                _add_branch(sandbox, "sub_board", parent_key)
    with action_cols[3]:
        if st.button("↺ Reset preview", use_container_width=True, key="hmi4_reset"):
            st.session_state["hmi_board_sandbox"] = deepcopy(persisted)
            st.session_state["hmi_selected_uid"] = "root"
            st.session_state["hmi_focus_circuit_id"] = None
            st.rerun()
    max_phase = root_plan.phase_balance.max_phase_current_a if root_plan is not None else None
    incomer = root_plan.incomer_candidate.breaker_rating_a if root_plan is not None else None
    circuit_count = len(calculated.circuit_contexts) if calculated is not None else 0
    unresolved = sum(1 for item in calculated.circuit_contexts if item.breaker_candidate_a is None or item.cable_mm2 is None) if calculated is not None else 0
    st.markdown(f'<div class="bp-kpi-strip"><div class="bp-kpi"><div class="bp-kpi-label">Max phase demand</div><div class="bp-kpi-value">{_fmt_a(max_phase)}</div><div class="bp-kpi-foot">live hierarchy</div></div><div class="bp-kpi"><div class="bp-kpi-label">Incomer candidate</div><div class="bp-kpi-value">{_fmt_rating(incomer)}</div><div class="bp-kpi-foot">planning only</div></div><div class="bp-kpi"><div class="bp-kpi-label">Final circuits</div><div class="bp-kpi-value">{circuit_count}</div><div class="bp-kpi-foot">calculated branches</div></div><div class="bp-kpi"><div class="bp-kpi-label">Needs attention</div><div class="bp-kpi-value">{unresolved}</div><div class="bp-kpi-foot">design scope</div></div></div>', unsafe_allow_html=True)
    hierarchy_col, schedule_col, properties_col = st.columns([1.0,1.65,1.25], gap="small")
    with hierarchy_col:
        with st.container(border=True):
            _render_hierarchy(board_id, branches)
    with schedule_col:
        with st.container(border=True):
            _render_schedule(calculated)
    with properties_col:
        with st.container(border=True):
            _render_properties(sandbox, branches, calculated, board_id, description)
    if focus_circuit_id:
        selection_title = f"Route focus · {focus_circuit_id}"
        selection_sub = "Complete source-to-load route"
        mode = "CIRCUIT FOCUS"
    elif selected is None:
        selection_title = f"{board_id} · {description}"
        selection_sub = "Board overview · downstream groups collapsed"
        mode = "BOARD OVERVIEW"
    else:
        selection_title = _branch_label(selected).strip()
        selection_sub = f"Selected {selected.get('kind','item').replace('_',' ')}"
        mode = "FIELD / EQUIPMENT FOCUS"
    st.markdown(f'<div class="bp-diagram-head"><div><div class="bp-diagram-title">Single-line workspace · {escape(selection_title)}</div><div class="bp-diagram-sub">{escape(selection_sub)}</div></div><span class="bp-diagram-mode">{mode}</span></div>', unsafe_allow_html=True)
    if calculation_error:
        st.warning(calculation_error)
    elif graph is not None:
        svg = render_hmi_single_line_svg(graph, selected_node_ids=_route_graph_nodes(graph, selected, focus_circuit_id))
        components.html(f'<style>html,body{{margin:0;background:#08131f}}.shell{{height:650px;width:100%;overflow:auto;border:1px solid #1d334d;border-radius:10px;background:#08131f;box-sizing:border-box}}svg{{min-width:100%;min-height:620px}}</style><div class="shell">{svg}</div>', height=670, scrolling=False)
    st.markdown('<div class="bp-callout warn"><b>Design preview</b> · Wide SLD layout. Hierarchy groups collapse above the diagram; circuit-table selection remains linked to route highlighting.</div>', unsafe_allow_html=True)
