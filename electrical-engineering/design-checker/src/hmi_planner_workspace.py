"""Experimental HMI Board Planner workspace used by the preview page."""
from __future__ import annotations

from copy import deepcopy
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from .board_persistence import load_last_board
from .hmi_single_line import render_hmi_single_line_svg
from .ui_theme import apply_theme
from .working_board_plan import calculate_working_board


_CSS = r"""
<style>
.stApp{
  background:
    radial-gradient(circle at 78% 4%, rgba(25,112,178,.12), transparent 31rem),
    radial-gradient(circle at 18% 82%, rgba(31,78,126,.09), transparent 38rem),
    linear-gradient(180deg,#06101c 0%,#071422 48%,#06111d 100%) !important;
}
[data-testid="stAppViewContainer"]:before{
  content:"";position:fixed;inset:0;pointer-events:none;opacity:.13;
  background-image:linear-gradient(rgba(92,137,181,.15) 1px,transparent 1px),linear-gradient(90deg,rgba(92,137,181,.12) 1px,transparent 1px);
  background-size:48px 48px;mask-image:linear-gradient(to bottom,rgba(0,0,0,.75),transparent 80%);
}
.block-container {max-width:1780px; padding-top:1.65rem !important; padding-bottom:2.25rem;}
.bp-topbar{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.72rem .9rem;margin:.15rem 0 .72rem;background:linear-gradient(180deg,rgba(19,34,56,.98),rgba(12,25,43,.98));border:1px solid #2b4362;border-radius:12px;box-shadow:0 14px 36px rgba(0,0,0,.2),inset 0 1px rgba(255,255,255,.03)}
.bp-brand{display:flex;align-items:center;gap:.72rem;min-width:0}.bp-brand-mark{width:36px;height:36px;display:grid;place-items:center;border-radius:9px;background:linear-gradient(145deg,#1c91dc,#0a5d97);color:#e6f6ff;box-shadow:inset 0 0 0 1px rgba(255,255,255,.13),0 7px 18px rgba(17,125,202,.2);font-size:1rem;font-weight:800}.bp-kicker{font-size:.61rem;color:#7b94b3;letter-spacing:.14em;text-transform:uppercase;font-weight:800}.bp-title{font-size:1.12rem;line-height:1.2;color:#f4f8ff;font-weight:730;letter-spacing:-.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bp-topmeta{display:flex;align-items:center;gap:.42rem;flex-wrap:wrap;justify-content:flex-end}.bp-pill{padding:.28rem .52rem;border-radius:6px;border:1px solid #2a415f;background:#0b1727;color:#a2b5cc;font-size:.66rem;font-weight:700}.bp-pill.live{color:#83e8b5;border-color:rgba(57,217,138,.3);background:rgba(57,217,138,.08)}.bp-pill.preview{color:#8fd1ff;border-color:rgba(54,167,255,.3);background:rgba(54,167,255,.08)}
.bp-toolbar{display:flex;align-items:center;justify-content:space-between;gap:.8rem;margin-bottom:.55rem;padding:.42rem .58rem;background:rgba(10,21,36,.92);border:1px solid #1d3049;border-radius:8px;backdrop-filter:blur(10px)}.bp-path{font-size:.69rem;color:#8da2bb}.bp-toolbar-note{font-size:.64rem;color:#647d9b}.bp-contextbar{display:flex;align-items:center;justify-content:space-between;gap:.7rem;margin:.15rem 0 .45rem;padding:.35rem .55rem;border-left:3px solid #36a7ff;background:rgba(54,167,255,.055);border-radius:0 7px 7px 0}.bp-contextbar strong{font-size:.68rem;color:#badfff}.bp-contextbar span{font-size:.63rem;color:#718aa7}
.bp-panel-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.75rem;padding:.05rem 0 .62rem;border-bottom:1px solid #1e314a;margin-bottom:.68rem}.bp-panel-title{font-size:.78rem;color:#eaf3ff;font-weight:760;letter-spacing:.01em;text-transform:uppercase}.bp-panel-sub{font-size:.66rem;color:#6f86a3;margin-top:.12rem;line-height:1.35}.bp-badge{font-size:.61rem;color:#8fd1ff;border:1px solid rgba(54,167,255,.25);background:rgba(54,167,255,.07);padding:.2rem .42rem;border-radius:5px;white-space:nowrap}
.bp-kpi-strip{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.48rem;margin:.3rem 0 .65rem}.bp-kpi{background:#0a1728;border:1px solid #1e334e;border-radius:8px;padding:.52rem .62rem;min-width:0}.bp-kpi-label{font-size:.58rem;color:#687f9b;text-transform:uppercase;letter-spacing:.08em;font-weight:780}.bp-kpi-value{font-size:1rem;color:#f1f7ff;font-weight:680;margin-top:.12rem}.bp-kpi-foot{font-size:.58rem;color:#5d738e;margin-top:.04rem}
.bp-selection{display:flex;gap:.5rem;align-items:center;padding:.5rem .62rem;margin:.35rem 0 .58rem;border:1px solid rgba(54,167,255,.27);background:linear-gradient(90deg,rgba(54,167,255,.11),rgba(54,167,255,.035));border-radius:8px}.bp-selection.focus{border-color:rgba(57,174,247,.58);box-shadow:0 0 0 1px rgba(57,174,247,.08),0 0 22px rgba(25,126,194,.08)}.bp-selection-dot{width:7px;height:7px;border-radius:50%;background:#40b3ff;box-shadow:0 0 0 4px rgba(54,167,255,.1)}.bp-selection-title{font-size:.72rem;color:#cfeaff;font-weight:700}.bp-selection-sub{font-size:.62rem;color:#7895b6}
.bp-callout{border-left:3px solid #36a7ff;background:rgba(54,167,255,.055);padding:.48rem .62rem;border-radius:0 7px 7px 0;font-size:.67rem;color:#89a5c3;line-height:1.4;margin-top:.55rem}.bp-callout.warn{border-left-color:#f7bf4f;background:rgba(247,191,79,.055);color:#b8a579}.bp-minihead{font-size:.62rem;color:#6f86a3;text-transform:uppercase;letter-spacing:.08em;font-weight:780;margin:.78rem 0 .35rem}
[data-testid="stHorizontalBlock"]:has(.bp-column-anchor){gap:.65rem!important;align-items:stretch}[data-testid="stHorizontalBlock"]:has(.bp-column-anchor)>div[data-testid="column"]>div{height:100%}[data-testid="stHorizontalBlock"]:has(.bp-column-anchor) [data-testid="stVerticalBlockBorderWrapper"]{min-height:730px;background:linear-gradient(180deg,rgba(13,26,44,.96),rgba(10,22,37,.97))!important;border-color:#223954!important;box-shadow:0 14px 34px rgba(0,0,0,.14),inset 0 1px rgba(255,255,255,.018);backdrop-filter:blur(8px)}
[data-testid="stRadio"] [role="radiogroup"]{display:flex;flex-direction:column;gap:.28rem}[data-testid="stRadio"] label{width:100%;min-height:34px;border-radius:6px;padding:.38rem .48rem!important;background:#0b1829;border:1px solid #1b304a}[data-testid="stRadio"] label:hover{background:#102139;border-color:#2d4b6e}[data-testid="stRadio"] label:has(input:checked){background:linear-gradient(90deg,rgba(54,167,255,.15),rgba(54,167,255,.05));border-color:#2d79ad;box-shadow:inset 3px 0 #36a7ff}[data-testid="stRadio"] label p{font-size:.69rem!important}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-baseweb="select"]>div{background:#081523!important;border-color:#243d5a!important}[data-testid="stTextInput"] label,[data-testid="stNumberInput"] label,[data-testid="stSelectbox"] label{font-size:.68rem!important;color:#8da2ba!important}div.stButton>button{border-radius:6px;min-height:34px;font-size:.7rem}
.bp-sld-shell{width:100%;height:510px;display:flex;align-items:flex-start;justify-content:center;overflow:auto;background:#08131f;border:1px solid #1d334d;border-radius:9px;box-shadow:inset 0 0 40px rgba(0,0,0,.12)}
@media(max-width:1100px){.bp-kpi-strip{grid-template-columns:repeat(2,1fr)}.bp-topbar{display:block}.bp-topmeta{justify-content:flex-start;margin-top:.55rem}}
</style>
"""


def _panel_header(title: str, subtitle: str, badge: str = "") -> None:
    badge_html = f'<span class="bp-badge">{escape(badge)}</span>' if badge else ""
    st.markdown(f'<div class="bp-panel-head"><div><div class="bp-panel-title">{escape(title)}</div><div class="bp-panel-sub">{escape(subtitle)}</div></div>{badge_html}</div>', unsafe_allow_html=True)


def _fmt_a(value) -> str:
    return "—" if value is None else f"{value:.1f} A"


def _fmt_rating(value) -> str:
    return "—" if value is None else f"{value:g} A"


def _fmt_cable(mm2, runs) -> str:
    if mm2 is None:
        return "—"
    count = runs or 1
    return f"{count} × {mm2:g} mm²" if count > 1 else f"{mm2:g} mm²"


def _branch_label(branch: dict, depth: int = 0) -> str:
    prefix = "  └─ " if depth else ""
    kind = branch.get("kind")
    if kind == "final":
        return f"{prefix}○ {branch.get('circuit_id', 'Circuit')} · {branch.get('description', '')}"
    if kind == "field":
        return f"{prefix}◇ {branch.get('field_id', 'Field')} · {branch.get('description', '')}"
    return f"{prefix}▣ {branch.get('sub_board_id', 'Sub-board')} · {branch.get('description', '')}"


def _ensure_state(saved: dict) -> None:
    identity = (saved.get("board_id"), saved.get("description"), len(saved.get("branches", [])) if isinstance(saved.get("branches"), list) else 0)
    if st.session_state.get("_hmi_preview_source_identity") != identity:
        st.session_state["hmi_board_sandbox"] = deepcopy(saved)
        st.session_state["_hmi_preview_source_identity"] = identity
        st.session_state["hmi_selected_uid"] = "root"
        st.session_state["hmi_focus_circuit_id"] = None


def _selected_branch(sandbox: dict):
    uid = st.session_state.get("hmi_selected_uid", "root")
    return next((branch for branch in sandbox.get("branches", []) if branch.get("uid") == uid), None)


def _depth(branch: dict, branches: list[dict]) -> int:
    by_uid = {item.get("uid"): item for item in branches}
    parent = branch.get("parent_key", "root")
    depth = 0
    seen = set()
    while parent != "root" and parent in by_uid and parent not in seen:
        seen.add(parent)
        depth += 1
        parent = by_uid[parent].get("parent_key", "root")
    return depth


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


def _base_graph_nodes(graph, selected: dict | None, focus_circuit_id: str | None) -> tuple[str, ...]:
    if focus_circuit_id:
        return tuple(node.node_id for node in graph.nodes if node.circuit_id == focus_circuit_id)
    if selected is None:
        return tuple(node.node_id for node in graph.nodes if node.kind in ("incomer", "busbar") and (node.board_ref or graph.board_id) == graph.board_id)
    kind = selected.get("kind")
    if kind == "final":
        cid = str(selected.get("circuit_id", ""))
        return tuple(node.node_id for node in graph.nodes if node.circuit_id == cid)
    if kind == "field":
        feeder = str(selected.get("feeder_id", "")); field_id = str(selected.get("field_id", ""))
        return tuple(node.node_id for node in graph.nodes if node.circuit_id == feeder or node.field_ref == field_id)
    feeder = str(selected.get("feeder_id", "")); board_ref = str(selected.get("sub_board_id", ""))
    return tuple(node.node_id for node in graph.nodes if node.circuit_id == feeder or node.board_ref == board_ref)


def _route_graph_nodes(graph, selected: dict | None, focus_circuit_id: str | None) -> tuple[str, ...]:
    """Return selected equipment plus its complete upstream path to the source."""
    node_ids = set(_base_graph_nodes(graph, selected, focus_circuit_id))
    for node_id in tuple(node_ids):
        node_ids.update(node.node_id for node in graph.ancestors_of(node_id))
    return tuple(node_ids)


def _allowed_additions(selected: dict | None) -> tuple[str, ...]:
    if selected is None:
        return ("circuit", "field", "sub_board")
    kind = selected.get("kind")
    if kind == "final":
        return tuple()
    if kind == "field":
        return ("circuit", "sub_board")
    return ("circuit", "field", "sub_board")


def _add_branch(sandbox: dict, kind: str, parent_key: str) -> None:
    branches = sandbox.setdefault("branches", [])
    uid = _next_uid(sandbox)
    if kind == "circuit":
        cid = _next_id(sandbox, "C", "circuit_id")
        branches.append({"uid":uid,"kind":"final","parent_key":parent_key,"circuit_id":cid,"description":"New circuit","mode":"auto","load_kw":5.0,"phase":"three","power_factor":0.9,"demand_factor":1.0,"material":"copper","phase_preference":"Auto","connection_option_id":None})
    elif kind == "field":
        feeder = _next_id(sandbox, "F", "feeder_id"); field_id = _next_id(sandbox, "FIELD", "field_id")
        branches.append({"uid":uid,"kind":"field","parent_key":parent_key,"feeder_id":feeder,"field_id":field_id,"description":"New field","material":"copper"})
    else:
        feeder = _next_id(sandbox, "SB", "feeder_id"); sub_id = _next_id(sandbox, "DB", "sub_board_id")
        branches.append({"uid":uid,"kind":"sub_board","parent_key":parent_key,"feeder_id":feeder,"sub_board_id":sub_id,"description":"New sub-board","material":"copper"})
    st.session_state["hmi_selected_uid"] = uid
    st.session_state["hmi_focus_circuit_id"] = None
    st.rerun()


def render_workspace() -> None:
    apply_theme()
    st.markdown(_CSS, unsafe_allow_html=True)
    try:
        persisted = load_last_board()
    except ValueError as exc:
        st.error(str(exc)); return
    if persisted is None:
        st.info("Create a working board in Board Planner first. The HMI preview uses that board as its starting point."); return

    _ensure_state(persisted)
    sandbox = st.session_state["hmi_board_sandbox"]
    branches = sandbox.setdefault("branches", [])
    selected = _selected_branch(sandbox)
    focus_circuit_id = st.session_state.get("hmi_focus_circuit_id")
    try:
        calculated = calculate_working_board(sandbox); graph = calculated.graph; root_plan = calculated.hierarchy.root.plan; calculation_error = None
    except (TypeError, ValueError) as exc:
        calculated = None; graph = None; root_plan = None; calculation_error = str(exc)

    board_id = str(sandbox.get("board_id", "Board")); description = str(sandbox.get("description", "Distribution board"))
    st.markdown(f'<div class="bp-topbar"><div class="bp-brand"><div class="bp-brand-mark">◈</div><div><div class="bp-kicker">Electrical distribution · design workstation</div><div class="bp-title">{escape(board_id)} · {escape(description)}</div></div></div><div class="bp-topmeta"><span class="bp-pill preview">HMI DESIGN PREVIEW</span><span class="bp-pill live">● LIVE CALCULATION</span><span class="bp-pill">{sandbox.get("line_to_line_voltage_v",400):g} V L-L</span><span class="bp-pill">{len(branches)} branches</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="bp-toolbar"><span class="bp-path">Project / Distribution / Board Planner / Working board</span><span class="bp-toolbar-note">Sandbox · changes here do not overwrite the production Board Planner</span></div>', unsafe_allow_html=True)

    allowed = _allowed_additions(selected)
    parent_key = "root" if selected is None else str(selected.get("uid"))
    context_name = "Main board" if selected is None else _branch_label(selected).strip()
    if allowed:
        st.markdown(f'<div class="bp-contextbar"><strong>Add downstream of {escape(context_name)}</strong><span>Only hierarchy-valid workflow actions are shown</span></div>', unsafe_allow_html=True)
        cols = st.columns([.78 if "circuit" in allowed else .01,.78 if "field" in allowed else .01,.9 if "sub_board" in allowed else .01,.9,4.2], gap="small")
        if "circuit" in allowed:
            with cols[0]:
                if st.button("＋ Circuit", use_container_width=True, type="primary"): _add_branch(sandbox,"circuit",parent_key)
        if "field" in allowed:
            with cols[1]:
                if st.button("＋ Field", use_container_width=True): _add_branch(sandbox,"field",parent_key)
        if "sub_board" in allowed:
            with cols[2]:
                if st.button("＋ Sub-board", use_container_width=True): _add_branch(sandbox,"sub_board",parent_key)
        with cols[3]:
            if st.button("↺ Reset preview", use_container_width=True):
                st.session_state["hmi_board_sandbox"] = deepcopy(persisted); st.session_state["hmi_selected_uid"] = "root"; st.session_state["hmi_focus_circuit_id"] = None; st.rerun()
    else:
        c1, c2 = st.columns([1.8,.8])
        with c1: st.markdown('<div class="bp-contextbar"><strong>Final circuit selected</strong><span>No downstream additions are applicable here</span></div>', unsafe_allow_html=True)
        with c2:
            if st.button("↺ Reset preview", use_container_width=True):
                st.session_state["hmi_board_sandbox"] = deepcopy(persisted); st.session_state["hmi_selected_uid"] = "root"; st.session_state["hmi_focus_circuit_id"] = None; st.rerun()

    left, center, right = st.columns([.82,2.18,1.0], gap="small")
    with left:
        st.markdown('<div class="bp-column-anchor"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            _panel_header("Hierarchy","Select equipment to inspect or edit.","NAVIGATION")
            options = ["root"] + [str(branch.get("uid")) for branch in branches]
            labels = {"root":f"▰ {board_id} · Main board"}; labels.update({str(branch.get("uid")):_branch_label(branch,_depth(branch,branches)) for branch in branches})
            current = st.session_state.get("hmi_selected_uid","root"); current = current if current in options else "root"
            chosen = st.radio("Hierarchy",options,index=options.index(current),format_func=lambda value:labels.get(value,value),label_visibility="collapsed",key="hmi_tree_radio_v3")
            if chosen != st.session_state.get("hmi_selected_uid"):
                st.session_state["hmi_selected_uid"] = chosen; st.session_state["hmi_focus_circuit_id"] = None; st.rerun()
            st.markdown('<div class="bp-callout">The hierarchy is the editing context. The circuit schedule can independently focus a route in the single-line without changing what you are editing.</div>', unsafe_allow_html=True)

    with center:
        st.markdown('<div class="bp-column-anchor"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            _panel_header("Single-line workspace","Click a schedule row to trace that circuit back to the source.","LIVE")
            max_phase = root_plan.phase_balance.max_phase_current_a if root_plan is not None else None; incomer = root_plan.incomer_candidate.breaker_rating_a if root_plan is not None else None
            circuit_count = len(calculated.circuit_contexts) if calculated is not None else 0; unresolved = sum(1 for item in calculated.circuit_contexts if item.breaker_candidate_a is None or item.cable_mm2 is None) if calculated is not None else 0
            st.markdown(f'<div class="bp-kpi-strip"><div class="bp-kpi"><div class="bp-kpi-label">Max phase demand</div><div class="bp-kpi-value">{_fmt_a(max_phase)}</div><div class="bp-kpi-foot">live hierarchy</div></div><div class="bp-kpi"><div class="bp-kpi-label">Incomer candidate</div><div class="bp-kpi-value">{_fmt_rating(incomer)}</div><div class="bp-kpi-foot">planning only</div></div><div class="bp-kpi"><div class="bp-kpi-label">Final circuits</div><div class="bp-kpi-value">{circuit_count}</div><div class="bp-kpi-foot">calculated branches</div></div><div class="bp-kpi"><div class="bp-kpi-label">Needs attention</div><div class="bp-kpi-value">{unresolved}</div><div class="bp-kpi-foot">design scope</div></div></div>', unsafe_allow_html=True)
            if focus_circuit_id:
                selection_title = f"Route focus · {focus_circuit_id}"; selection_sub = "Selected from circuit schedule · complete upstream path highlighted"; selection_class = "bp-selection focus"
            else:
                selection_title = f"{board_id} · {description}" if selected is None else _branch_label(selected).strip(); selection_sub = "Main board / busbar context" if selected is None else f"Selected {selected.get('kind','item').replace('_',' ')}"; selection_class = "bp-selection"
            st.markdown(f'<div class="{selection_class}"><span class="bp-selection-dot"></span><div><div class="bp-selection-title">{escape(selection_title)}</div><div class="bp-selection-sub">{escape(selection_sub)}</div></div></div>', unsafe_allow_html=True)
            if calculation_error: st.warning(calculation_error)
            elif graph is not None:
                svg = render_hmi_single_line_svg(graph, selected_node_ids=_route_graph_nodes(graph,selected,focus_circuit_id))
                components.html(f'<div class="bp-sld-shell">{svg}</div>',height=525,scrolling=False)
            st.markdown('<div class="bp-minihead">Calculated circuit schedule · select a row to trace</div>',unsafe_allow_html=True)
            schedule=[]
            if calculated is not None:
                for context in calculated.circuit_contexts:
                    schedule.append({"Circuit":context.circuit_id,"Ib":_fmt_a(context.design_current_a),"Breaker":_fmt_rating(context.breaker_candidate_a),"Cable":_fmt_cable(context.cable_mm2,context.cable_runs)})
            event = st.dataframe(schedule,use_container_width=True,hide_index=True,height=min(250,72+max(1,len(schedule))*35),on_select="rerun",selection_mode="single-row",key="hmi_schedule_select")
            rows = []
            try:
                rows = list(event.selection.rows)
            except (AttributeError, TypeError):
                if isinstance(event, dict): rows = list(event.get("selection", {}).get("rows", []))
            if rows and 0 <= rows[0] < len(schedule):
                clicked_circuit = str(schedule[rows[0]]["Circuit"])
                if clicked_circuit != st.session_state.get("hmi_focus_circuit_id"):
                    st.session_state["hmi_focus_circuit_id"] = clicked_circuit; st.rerun()
            elif not rows and st.session_state.get("hmi_focus_circuit_id") is not None:
                st.session_state["hmi_focus_circuit_id"] = None; st.rerun()

    with right:
        st.markdown('<div class="bp-column-anchor"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            selected = _selected_branch(sandbox)
            if selected is None:
                _panel_header("Board properties","Edit the selected main board context.","INSPECTOR")
                bid=st.text_input("Board ID",value=board_id,key="hmi3_board_id"); desc=st.text_input("Description",value=description,key="hmi3_board_desc"); v1,v2=st.columns(2)
                with v1: vll=st.number_input("L-L voltage (V)",min_value=1.0,value=float(sandbox.get("line_to_line_voltage_v",400)),step=10.0,key="hmi3_vll")
                with v2: vln=st.number_input("L-N voltage (V)",min_value=1.0,value=float(sandbox.get("line_to_neutral_voltage_v",230)),step=10.0,key="hmi3_vln")
                if st.button("Apply board changes",use_container_width=True,type="primary"):
                    sandbox.update({"board_id":bid.strip() or board_id,"description":desc.strip() or description,"line_to_line_voltage_v":float(vll),"line_to_neutral_voltage_v":float(vln)}); st.rerun()
            else:
                kind=str(selected.get("kind","item")); _panel_header("Properties","Selected equipment and live design inputs.",kind.replace("_"," ").upper())
                if kind=="final":
                    cid=st.text_input("Circuit ID",value=str(selected.get("circuit_id","")),key=f"hmi3_cid_{selected['uid']}"); desc=st.text_input("Description",value=str(selected.get("description","")),key=f"hmi3_desc_{selected['uid']}"); load=st.number_input("Connected load (kW)",min_value=.1,value=float(selected.get("load_kw",5)),step=1.0,key=f"hmi3_load_{selected['uid']}"); a,b=st.columns(2)
                    with a: phase=st.selectbox("Phase",["single","three"],index=0 if selected.get("phase")=="single" else 1,format_func=lambda x:"1P" if x=="single" else "3P",key=f"hmi3_phase_{selected['uid']}")
                    with b: material=st.selectbox("Conductor",["copper","aluminium"],index=1 if selected.get("material")=="aluminium" else 0,format_func=lambda x:"Aluminium" if x=="aluminium" else "Copper",key=f"hmi3_mat_{selected['uid']}")
                    pf=st.number_input("Power factor",min_value=.01,max_value=1.0,value=float(selected.get("power_factor",.9)),step=.01,key=f"hmi3_pf_{selected['uid']}"); demand=st.number_input("Demand factor",min_value=.01,max_value=1.0,value=float(selected.get("demand_factor",1)),step=.05,key=f"hmi3_df_{selected['uid']}")
                    if st.button("Apply circuit changes",use_container_width=True,type="primary"):
                        selected.update({"circuit_id":cid.strip() or selected.get("circuit_id"),"description":desc,"load_kw":float(load),"phase":phase,"material":material,"power_factor":float(pf),"demand_factor":float(demand)}); st.rerun()
                elif kind=="field":
                    feeder=st.text_input("Feeder ID",value=str(selected.get("feeder_id","")),key=f"hmi3_feed_{selected['uid']}"); fid=st.text_input("Field ID",value=str(selected.get("field_id","")),key=f"hmi3_field_{selected['uid']}"); desc=st.text_input("Description",value=str(selected.get("description","")),key=f"hmi3_fdesc_{selected['uid']}"); material=st.selectbox("Feeder conductor",["copper","aluminium"],index=1 if selected.get("material")=="aluminium" else 0,key=f"hmi3_fmat_{selected['uid']}")
                    if st.button("Apply field changes",use_container_width=True,type="primary"):
                        selected.update({"feeder_id":feeder.strip() or selected.get("feeder_id"),"field_id":fid.strip() or selected.get("field_id"),"description":desc,"material":material}); st.rerun()
                else:
                    feeder=st.text_input("Feeder ID",value=str(selected.get("feeder_id","")),key=f"hmi3_sbfeed_{selected['uid']}"); sid=st.text_input("Sub-board ID",value=str(selected.get("sub_board_id","")),key=f"hmi3_sbid_{selected['uid']}"); desc=st.text_input("Description",value=str(selected.get("description","")),key=f"hmi3_sbdesc_{selected['uid']}")
                    if st.button("Apply sub-board changes",use_container_width=True,type="primary"):
                        selected.update({"feeder_id":feeder.strip() or selected.get("feeder_id"),"sub_board_id":sid.strip() or selected.get("sub_board_id"),"description":desc}); st.rerun()
                st.divider()
                if st.button("Remove selected item",use_container_width=True):
                    selected_uid=selected.get("uid"); descendants={selected_uid}; changed=True
                    while changed:
                        changed=False
                        for item in branches:
                            if item.get("parent_key") in descendants and item.get("uid") not in descendants: descendants.add(item.get("uid")); changed=True
                    sandbox["branches"]=[item for item in branches if item.get("uid") not in descendants]; st.session_state["hmi_selected_uid"]="root"; st.session_state["hmi_focus_circuit_id"] = None; st.rerun()
                if calculated is not None and kind=="final":
                    context=calculated.context_by_circuit_id.get(str(selected.get("circuit_id","")))
                    if context is not None: st.markdown(f'<div class="bp-callout"><b style="color:#bcdcff">Calculated now</b><br>Ib {_fmt_a(context.design_current_a)} · breaker {_fmt_rating(context.breaker_candidate_a)} · cable {_fmt_cable(context.cable_mm2,context.cable_runs)}</div>',unsafe_allow_html=True)

    st.markdown('<div class="bp-callout warn"><b>Design preview</b> · Schedule-to-diagram route tracing is now active. This interaction model can later be reused for protection failures, selectivity chains and other review states.</div>',unsafe_allow_html=True)
