"""Experimental HMI-grade Board Planner workspace.

This page mirrors the Board Planner workflow against a session-only sandbox copy of the
real persisted board. It exists so the visual hierarchy and interaction model can be
reviewed before replacing the production planner.
"""
from __future__ import annotations

from copy import deepcopy

import streamlit as st
import streamlit.components.v1 as components

from src.board_persistence import load_last_board
from src.single_line_svg import render_board_graph_svg
from src.ui_theme import apply_theme
from src.working_board_plan import calculate_working_board

st.set_page_config(
    page_title="Board Planner · HMI Preview",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()

st.markdown(
    r"""
<style>
/* Planner-specific workstation composition */
.block-container {max-width: 1780px; padding-top:.75rem; padding-bottom:2rem;}

.bp-topbar {
  display:flex; align-items:center; justify-content:space-between; gap:1rem;
  padding:.68rem .85rem; margin-bottom:.75rem;
  background:linear-gradient(180deg, rgba(19,34,56,.96), rgba(13,26,44,.96));
  border:1px solid #2b4362; border-radius:12px;
  box-shadow:0 12px 34px rgba(0,0,0,.18), inset 0 1px rgba(255,255,255,.025);
}
.bp-brand {display:flex; align-items:center; gap:.75rem; min-width:0;}
.bp-brand-mark {
  width:34px; height:34px; display:grid; place-items:center; border-radius:9px;
  background:linear-gradient(145deg,#1789d6,#0b5d96); color:#dff3ff;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.12), 0 6px 18px rgba(17,125,202,.2);
  font-size:1rem; font-weight:800;
}
.bp-kicker {font-size:.61rem; color:#6f88a8; letter-spacing:.13em; text-transform:uppercase; font-weight:800;}
.bp-title {font-size:1.12rem; line-height:1.2; color:#f4f8ff; font-weight:720; letter-spacing:-.02em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.bp-topmeta {display:flex; align-items:center; gap:.42rem; flex-wrap:wrap; justify-content:flex-end;}
.bp-pill {padding:.28rem .52rem; border-radius:6px; border:1px solid #2a415f; background:#0b1727; color:#9fb2ca; font-size:.67rem; font-weight:700;}
.bp-pill.live {color:#83e8b5; border-color:rgba(57,217,138,.3); background:rgba(57,217,138,.08);}
.bp-pill.preview {color:#8fd1ff; border-color:rgba(54,167,255,.3); background:rgba(54,167,255,.08);}

.bp-toolbar {
  display:flex; align-items:center; justify-content:space-between; gap:.8rem;
  margin-bottom:.7rem; padding:.42rem .55rem;
  background:#0a1524; border:1px solid #1d3049; border-radius:9px;
}
.bp-toolbar-left {display:flex; align-items:center; gap:.55rem; min-width:0;}
.bp-path {font-size:.71rem; color:#8da2bb; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.bp-toolbar-note {font-size:.65rem; color:#647d9b;}

.bp-panel-head {display:flex; align-items:flex-start; justify-content:space-between; gap:.75rem; padding:.05rem 0 .62rem 0; border-bottom:1px solid #1e314a; margin-bottom:.68rem;}
.bp-panel-title {font-size:.78rem; color:#eaf3ff; font-weight:760; letter-spacing:.01em; text-transform:uppercase;}
.bp-panel-sub {font-size:.66rem; color:#6f86a3; margin-top:.12rem; line-height:1.35;}
.bp-badge {font-size:.61rem; color:#8fd1ff; border:1px solid rgba(54,167,255,.25); background:rgba(54,167,255,.07); padding:.2rem .42rem; border-radius:5px; white-space:nowrap;}

.bp-kpi-strip {display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.48rem; margin:.3rem 0 .65rem 0;}
.bp-kpi {background:#0a1728; border:1px solid #1e334e; border-radius:8px; padding:.52rem .62rem; min-width:0;}
.bp-kpi-label {font-size:.58rem; color:#687f9b; text-transform:uppercase; letter-spacing:.08em; font-weight:780;}
.bp-kpi-value {font-size:1rem; color:#f1f7ff; font-weight:680; margin-top:.12rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.bp-kpi-foot {font-size:.58rem; color:#5d738e; margin-top:.04rem;}

.bp-selection {
  display:flex; gap:.5rem; align-items:center; padding:.55rem .62rem; margin:.45rem 0 .65rem 0;
  border:1px solid rgba(54,167,255,.27); background:linear-gradient(90deg,rgba(54,167,255,.11),rgba(54,167,255,.035)); border-radius:8px;
}
.bp-selection-dot {width:7px; height:7px; border-radius:50%; background:#40b3ff; box-shadow:0 0 0 4px rgba(54,167,255,.1);}
.bp-selection-title {font-size:.72rem; color:#cfeaff; font-weight:700;}
.bp-selection-sub {font-size:.62rem; color:#7895b6;}

.bp-callout {border-left:3px solid #36a7ff; background:rgba(54,167,255,.055); padding:.48rem .62rem; border-radius:0 7px 7px 0; font-size:.67rem; color:#89a5c3; line-height:1.4; margin-top:.55rem;}
.bp-callout.warn {border-left-color:#f7bf4f; background:rgba(247,191,79,.055); color:#b8a579;}

/* Make the three work areas look like one composed workstation */
[data-testid="stHorizontalBlock"]:has(.bp-column-anchor) {gap:.65rem !important; align-items:stretch;}
[data-testid="stHorizontalBlock"]:has(.bp-column-anchor) > div[data-testid="column"] > div {height:100%;}
[data-testid="stHorizontalBlock"]:has(.bp-column-anchor) [data-testid="stVerticalBlockBorderWrapper"] {
  min-height:720px; background:linear-gradient(180deg,#0d1a2c,#0a1625) !important;
  border-color:#223954 !important; box-shadow:0 14px 34px rgba(0,0,0,.14), inset 0 1px rgba(255,255,255,.018);
}

/* Radio items become hierarchy rows */
[data-testid="stRadio"] [role="radiogroup"] {display:flex; flex-direction:column; gap:.28rem;}
[data-testid="stRadio"] label {width:100%; min-height:34px; border-radius:6px; padding:.38rem .48rem !important; background:#0b1829; border:1px solid #1b304a;}
[data-testid="stRadio"] label:hover {background:#102139; border-color:#2d4b6e;}
[data-testid="stRadio"] label:has(input:checked) {background:linear-gradient(90deg,rgba(54,167,255,.15),rgba(54,167,255,.05)); border-color:#2d79ad; box-shadow:inset 3px 0 #36a7ff;}
[data-testid="stRadio"] label p {font-size:.7rem !important;}

/* Slightly more industrial inputs */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-baseweb="select"] > div {background:#081523 !important; border-color:#243d5a !important;}
[data-testid="stTextInput"] label, [data-testid="stNumberInput"] label, [data-testid="stSelectbox"] label {font-size:.68rem !important; text-transform:none; letter-spacing:.01em; color:#8da2ba !important;}
div.stButton > button {border-radius:6px; min-height:34px; font-size:.7rem;}

.bp-canvas-shell {background:#08131f; border:1px solid #1d334d; border-radius:9px; padding:.35rem; min-height:500px; position:relative; overflow:hidden;}
.bp-canvas-shell:before {content:""; position:absolute; inset:0; pointer-events:none; opacity:.23; background-image:linear-gradient(#18314b 1px, transparent 1px), linear-gradient(90deg,#18314b 1px,transparent 1px); background-size:28px 28px; mask-image:linear-gradient(to bottom,black,transparent 92%);}

@media (max-width:1100px){.bp-kpi-strip{grid-template-columns:repeat(2,1fr)} .bp-topbar{display:block}.bp-topmeta{justify-content:flex-start;margin-top:.55rem}}
</style>
""",
    unsafe_allow_html=True,
)


def _panel_header(title: str, subtitle: str, badge: str = "") -> None:
    badge_html = f'<span class="bp-badge">{badge}</span>' if badge else ""
    st.markdown(
        f'<div class="bp-panel-head"><div><div class="bp-panel-title">{title}</div><div class="bp-panel-sub">{subtitle}</div></div>{badge_html}</div>',
        unsafe_allow_html=True,
    )


def _fmt_a(value) -> str:
    return "—" if value is None else f"{value:.1f} A"


def _fmt_rating(value) -> str:
    return "—" if value is None else f"{value:g} A"


def _fmt_cable(mm2, runs) -> str:
    if mm2 is None:
        return "—"
    count = runs or 1
    return f"{count} × {mm2:g} mm²" if count > 1 else f"{mm2:g} mm²"


def _branch_label(branch: dict) -> str:
    kind = branch.get("kind")
    if kind == "final":
        return f"◦  {branch.get('circuit_id', 'Circuit')}  ·  {branch.get('description', '')}"
    if kind == "field":
        return f"◇  {branch.get('field_id', 'Field')}  ·  {branch.get('description', '')}"
    if kind == "sub_board":
        return f"▣  {branch.get('sub_board_id', 'Sub-board')}  ·  {branch.get('description', '')}"
    return str(branch.get("uid", "Item"))


def _ensure_preview_state(saved: dict) -> None:
    identity = (
        saved.get("board_id"),
        saved.get("description"),
        len(saved.get("branches", [])) if isinstance(saved.get("branches"), list) else 0,
    )
    if st.session_state.get("_hmi_preview_source_identity") != identity:
        st.session_state["hmi_board_sandbox"] = deepcopy(saved)
        st.session_state["_hmi_preview_source_identity"] = identity
        st.session_state["hmi_selected_uid"] = "root"


def _selected_branch(sandbox: dict):
    uid = st.session_state.get("hmi_selected_uid", "root")
    for branch in sandbox.get("branches", []):
        if branch.get("uid") == uid:
            return branch
    return None


def _next_uid(sandbox: dict) -> str:
    current = int(sandbox.get("uid_counter", 100)) + 1
    sandbox["uid_counter"] = current
    return f"b{current}"


def _next_id(sandbox: dict, prefix: str, key: str) -> str:
    used = {str(item.get(key, "")).strip() for item in sandbox.get("branches", [])}
    number = 1
    while f"{prefix}-{number:02d}" in used:
        number += 1
    return f"{prefix}-{number:02d}"


try:
    persisted = load_last_board()
except ValueError as exc:
    persisted = None
    st.error(str(exc))

if persisted is None:
    st.info("Create a working board in Board Planner first. The HMI preview uses that board as its starting point.")
    st.stop()

_ensure_preview_state(persisted)
sandbox = st.session_state["hmi_board_sandbox"]
branches = sandbox.setdefault("branches", [])

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

st.markdown(
    f"""
    <div class="bp-topbar">
      <div class="bp-brand">
        <div class="bp-brand-mark">◈</div>
        <div>
          <div class="bp-kicker">Electrical distribution · design workstation</div>
          <div class="bp-title">{board_id} · {description}</div>
        </div>
      </div>
      <div class="bp-topmeta">
        <span class="bp-pill preview">HMI DESIGN PREVIEW</span>
        <span class="bp-pill live">● LIVE CALCULATION</span>
        <span class="bp-pill">{sandbox.get('line_to_line_voltage_v', 400):g} V L-L</span>
        <span class="bp-pill">{len(branches)} branches</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="bp-toolbar">
      <div class="bp-toolbar-left"><span class="bp-path">Project / Distribution / Board Planner / Working board</span></div>
      <div class="bp-toolbar-note">Sandbox · changes here do not overwrite the production Board Planner</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Top command row: keep the common actions close to the workspace, like an engineering toolbar.
a1, a2, a3, a4, spacer = st.columns([.8, .8, .9, .9, 4.2], gap="small")
with a1:
    if st.button("＋ Circuit", use_container_width=True, type="primary"):
        uid = _next_uid(sandbox)
        circuit_id = _next_id(sandbox, "C", "circuit_id")
        branches.append({
            "uid": uid,
            "kind": "final",
            "parent_key": "root",
            "circuit_id": circuit_id,
            "description": "New circuit",
            "mode": "auto",
            "load_kw": 5.0,
            "phase": "three",
            "power_factor": 0.9,
            "demand_factor": 1.0,
            "material": "copper",
            "phase_preference": "Auto",
            "connection_option_id": None,
        })
        st.session_state["hmi_selected_uid"] = uid
        st.rerun()
with a2:
    if st.button("＋ Field", use_container_width=True):
        uid = _next_uid(sandbox)
        feeder_id = _next_id(sandbox, "F", "feeder_id")
        field_id = _next_id(sandbox, "FIELD", "field_id")
        branches.append({
            "uid": uid,
            "kind": "field",
            "parent_key": "root",
            "feeder_id": feeder_id,
            "field_id": field_id,
            "description": "New field",
            "material": "copper",
        })
        st.session_state["hmi_selected_uid"] = uid
        st.rerun()
with a3:
    if st.button("＋ Sub-board", use_container_width=True):
        uid = _next_uid(sandbox)
        feeder_id = _next_id(sandbox, "SB", "feeder_id")
        sub_id = _next_id(sandbox, "DB", "sub_board_id")
        branches.append({
            "uid": uid,
            "kind": "sub_board",
            "parent_key": "root",
            "feeder_id": feeder_id,
            "sub_board_id": sub_id,
            "description": "New sub-board",
            "material": "copper",
        })
        st.session_state["hmi_selected_uid"] = uid
        st.rerun()
with a4:
    if st.button("↺ Reset preview", use_container_width=True):
        st.session_state["hmi_board_sandbox"] = deepcopy(persisted)
        st.session_state["hmi_selected_uid"] = "root"
        st.rerun()

# Three-pane engineering workstation.
left, center, right = st.columns([.82, 2.18, 1.0], gap="small")

with left:
    st.markdown('<div class="bp-column-anchor"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        _panel_header("Hierarchy", "Select equipment to inspect or edit.", "NAVIGATION")
        options = ["root"] + [str(branch.get("uid")) for branch in branches]
        labels = {"root": f"▰  {board_id}  ·  Main board"}
        labels.update({str(branch.get("uid")): _branch_label(branch) for branch in branches})
        current_uid = st.session_state.get("hmi_selected_uid", "root")
        if current_uid not in options:
            current_uid = "root"
        selected_uid = st.radio(
            "Hierarchy",
            options=options,
            index=options.index(current_uid),
            format_func=lambda value: labels.get(value, value),
            label_visibility="collapsed",
            key="hmi_tree_radio",
        )
        if selected_uid != st.session_state.get("hmi_selected_uid"):
            st.session_state["hmi_selected_uid"] = selected_uid
            st.rerun()

        st.markdown('<div class="bp-callout">Selection drives both the central engineering context and the property inspector. The goal is one stable workspace instead of navigating through repeated forms.</div>', unsafe_allow_html=True)

with center:
    st.markdown('<div class="bp-column-anchor"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        _panel_header("Single-line workspace", "Topology and calculated design context stay central while you edit.", "LIVE")

        max_phase = root_plan.phase_balance.max_phase_current_a if root_plan is not None else None
        incomer = root_plan.incomer_candidate.breaker_rating_a if root_plan is not None else None
        circuit_count = len(calculated.circuit_contexts) if calculated is not None else 0
        unresolved = 0
        if calculated is not None:
            unresolved = sum(1 for item in calculated.circuit_contexts if item.breaker_candidate_a is None or item.cable_mm2 is None)

        st.markdown(
            f"""
            <div class="bp-kpi-strip">
              <div class="bp-kpi"><div class="bp-kpi-label">Max phase demand</div><div class="bp-kpi-value">{_fmt_a(max_phase)}</div><div class="bp-kpi-foot">live hierarchy</div></div>
              <div class="bp-kpi"><div class="bp-kpi-label">Incomer candidate</div><div class="bp-kpi-value">{_fmt_rating(incomer)}</div><div class="bp-kpi-foot">planning only</div></div>
              <div class="bp-kpi"><div class="bp-kpi-label">Final circuits</div><div class="bp-kpi-value">{circuit_count}</div><div class="bp-kpi-foot">calculated branches</div></div>
              <div class="bp-kpi"><div class="bp-kpi-label">Needs attention</div><div class="bp-kpi-value">{unresolved}</div><div class="bp-kpi-foot">current design scope</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected = _selected_branch(sandbox)
        if selected is None:
            selection_title = f"{board_id} · {description}"
            selection_sub = "Main board / busbar context"
        else:
            selection_title = _branch_label(selected).replace("◦  ", "").replace("◇  ", "").replace("▣  ", "")
            selection_sub = f"Selected {selected.get('kind', 'item').replace('_', ' ')}"
        st.markdown(
            f'<div class="bp-selection"><span class="bp-selection-dot"></span><div><div class="bp-selection-title">{selection_title}</div><div class="bp-selection-sub">{selection_sub}</div></div></div>',
            unsafe_allow_html=True,
        )

        if calculation_error:
            st.warning(calculation_error)
        elif graph is not None:
            svg = render_board_graph_svg(graph, tuple())
            components.html(
                f'<div style="width:100%;height:505px;display:flex;align-items:center;justify-content:center;overflow:hidden;background:#08131f;border:1px solid #1d334d;border-radius:9px;">{svg}</div>',
                height=520,
                scrolling=False,
            )

        if calculated is not None:
            with st.expander("Circuit schedule · calculated context", expanded=False):
                schedule = []
                for context in calculated.circuit_contexts:
                    schedule.append({
                        "Circuit": context.circuit_id,
                        "Ib": _fmt_a(context.design_current_a),
                        "Breaker": _fmt_rating(context.breaker_candidate_a),
                        "Cable": _fmt_cable(context.cable_mm2, context.cable_runs),
                    })
                st.dataframe(schedule, use_container_width=True, hide_index=True)

with right:
    st.markdown('<div class="bp-column-anchor"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        selected = _selected_branch(sandbox)
        if selected is None:
            _panel_header("Board properties", "Edit the selected main board context.", "INSPECTOR")
            new_board_id = st.text_input("Board ID", value=board_id, key="hmi_board_id")
            new_description = st.text_input("Description", value=description, key="hmi_board_desc")
            v1, v2 = st.columns(2)
            with v1:
                new_vll = st.number_input("L-L voltage (V)", min_value=1.0, value=float(sandbox.get("line_to_line_voltage_v", 400.0)), step=10.0, key="hmi_vll")
            with v2:
                new_vln = st.number_input("L-N voltage (V)", min_value=1.0, value=float(sandbox.get("line_to_neutral_voltage_v", 230.0)), step=10.0, key="hmi_vln")
            if st.button("Apply board changes", use_container_width=True, type="primary"):
                sandbox["board_id"] = new_board_id.strip() or board_id
                sandbox["description"] = new_description.strip() or description
                sandbox["line_to_line_voltage_v"] = float(new_vll)
                sandbox["line_to_neutral_voltage_v"] = float(new_vln)
                st.rerun()
            st.markdown('<div class="bp-callout">The inspector is intentionally narrow: selection stays visible in the middle while properties change here. This is the interaction pattern I would carry into the production planner.</div>', unsafe_allow_html=True)
        else:
            kind = str(selected.get("kind", "item"))
            _panel_header("Properties", "Selected equipment and live design inputs.", kind.replace("_", " ").upper())

            if kind == "final":
                cid = st.text_input("Circuit ID", value=str(selected.get("circuit_id", "")), key=f"hmi_cid_{selected['uid']}")
                desc = st.text_input("Description", value=str(selected.get("description", "")), key=f"hmi_desc_{selected['uid']}")
                load_kw = st.number_input("Connected load (kW)", min_value=.1, value=float(selected.get("load_kw", 5.0)), step=1.0, key=f"hmi_load_{selected['uid']}")
                c1, c2 = st.columns(2)
                with c1:
                    phase = st.selectbox("Phase", ["single", "three"], index=0 if selected.get("phase") == "single" else 1, format_func=lambda x: "1P" if x == "single" else "3P", key=f"hmi_phase_{selected['uid']}")
                with c2:
                    material = st.selectbox("Conductor", ["copper", "aluminium"], index=1 if selected.get("material") == "aluminium" else 0, format_func=lambda x: "Aluminium" if x == "aluminium" else "Copper", key=f"hmi_mat_{selected['uid']}")
                pf = st.number_input("Power factor", min_value=.01, max_value=1.0, value=float(selected.get("power_factor", .9)), step=.01, key=f"hmi_pf_{selected['uid']}")
                demand = st.number_input("Demand factor", min_value=.01, max_value=1.0, value=float(selected.get("demand_factor", 1.0)), step=.05, key=f"hmi_df_{selected['uid']}")
                if st.button("Apply circuit changes", use_container_width=True, type="primary"):
                    selected.update({"circuit_id": cid.strip() or selected.get("circuit_id"), "description": desc, "load_kw": float(load_kw), "phase": phase, "material": material, "power_factor": float(pf), "demand_factor": float(demand)})
                    st.rerun()
            elif kind == "field":
                feeder = st.text_input("Feeder ID", value=str(selected.get("feeder_id", "")), key=f"hmi_feeder_{selected['uid']}")
                field_id = st.text_input("Field ID", value=str(selected.get("field_id", "")), key=f"hmi_field_{selected['uid']}")
                desc = st.text_input("Description", value=str(selected.get("description", "")), key=f"hmi_fdesc_{selected['uid']}")
                material = st.selectbox("Feeder conductor", ["copper", "aluminium"], index=1 if selected.get("material") == "aluminium" else 0, key=f"hmi_fmat_{selected['uid']}")
                if st.button("Apply field changes", use_container_width=True, type="primary"):
                    selected.update({"feeder_id": feeder.strip() or selected.get("feeder_id"), "field_id": field_id.strip() or selected.get("field_id"), "description": desc, "material": material})
                    st.rerun()
            elif kind == "sub_board":
                feeder = st.text_input("Feeder ID", value=str(selected.get("feeder_id", "")), key=f"hmi_sbfeed_{selected['uid']}")
                sub_id = st.text_input("Sub-board ID", value=str(selected.get("sub_board_id", "")), key=f"hmi_sbid_{selected['uid']}")
                desc = st.text_input("Description", value=str(selected.get("description", "")), key=f"hmi_sbdesc_{selected['uid']}")
                if st.button("Apply sub-board changes", use_container_width=True, type="primary"):
                    selected.update({"feeder_id": feeder.strip() or selected.get("feeder_id"), "sub_board_id": sub_id.strip() or selected.get("sub_board_id"), "description": desc})
                    st.rerun()

            st.divider()
            if st.button("Remove selected item", use_container_width=True):
                selected_uid = selected.get("uid")
                descendants = {selected_uid}
                changed = True
                while changed:
                    changed = False
                    for item in branches:
                        if item.get("parent_key") in descendants and item.get("uid") not in descendants:
                            descendants.add(item.get("uid"))
                            changed = True
                sandbox["branches"] = [item for item in branches if item.get("uid") not in descendants]
                st.session_state["hmi_selected_uid"] = "root"
                st.rerun()

            if calculated is not None and kind == "final":
                context = calculated.context_by_circuit_id.get(str(selected.get("circuit_id", "")))
                if context is not None:
                    st.markdown(
                        f'<div class="bp-callout"><b style="color:#bcdcff">Calculated now</b><br>Ib {_fmt_a(context.design_current_a)} · breaker {_fmt_rating(context.breaker_candidate_a)} · cable {_fmt_cable(context.cable_mm2, context.cable_runs)}</div>',
                        unsafe_allow_html=True,
                    )

st.markdown(
    '<div class="bp-callout warn"><b>Design review note</b> · This page is intentionally a sandbox. The next step is visual/interaction feedback, then the approved layout will be migrated into the production Board Planner with its full hierarchy editing behavior.</div>',
    unsafe_allow_html=True,
)
