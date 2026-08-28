"""Hierarchy-first board planning UI with live Auto/Manual design."""
import streamlit as st
import streamlit.components.v1 as components

from src.board_graph import (
    add_field_feeder,
    add_radial_circuit,
    add_sub_board_feeder,
    enrich_graph_with_plan,
    make_radial_board_graph,
)
from src.board_planner import (
    BoardPhasePreference,
    BoardPlanRequest,
    calculate_board_plan,
)
from src.branch_engine import FinalBranchDesignRequest, calculate_final_branch
from src.connection import connection_options_for_phase
from src.single_line_svg import render_board_graph_svg

st.set_page_config(
    page_title="Board Planner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.block-container {max-width: 1540px; padding-top: 1.35rem; padding-bottom: 3rem;}
.hero {padding: 0.35rem 0 0.9rem 0;}
.hero h1 {margin:0; font-size:2.2rem; letter-spacing:-0.03em;}
.hero p {margin:.45rem 0 0 0; color:#94a3b8; font-size:.98rem;}
.eyebrow {font-size:.72rem; font-weight:700; letter-spacing:.11em; text-transform:uppercase; color:#64748b; margin-bottom:.32rem;}
[data-baseweb="select"] > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {border-radius:10px !important;}
[data-testid="stNumberInput"], [data-testid="stSelectbox"], [data-testid="stTextInput"] {max-width:310px;}
div.stButton > button {min-height:2.72rem; border-radius:12px; font-weight:700;}
[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stExpander"] {border-radius:12px; border-color:#334155;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px; background:#111827; border-color:#263449;}
[data-testid="stVerticalBlockBorderWrapper"] > div {padding:1rem 1.15rem;}
[data-testid="stMetric"] {background:#111827; border:1px solid #263449; border-radius:14px; padding:.9rem;}
.tree-note {color:#64748b; font-size:.82rem; margin-top:-.35rem;}
.workflow-note {color:#7f8da3; font-size:.8rem;}
.derived-title {font-size:.74rem; letter-spacing:.08em; text-transform:uppercase; color:#7f8da3; margin-top:.7rem; margin-bottom:.35rem;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """<div class="hero"><div class="eyebrow">Electrical engineering · Board hierarchy</div><h1>⚡ Board Planner</h1><p>Add an outlet, field or sub-board, adjust its properties, then check how it sits in the live diagram below.</p></div>""",
    unsafe_allow_html=True,
)


def default_branches():
    """Start a new board without demo branches."""
    return []


if "tree_board_branches" not in st.session_state:
    st.session_state["tree_board_branches"] = default_branches()
if "tree_uid_counter" not in st.session_state:
    st.session_state["tree_uid_counter"] = 100

branches = st.session_state["tree_board_branches"]
for branch in branches:
    if branch.get("kind") == "final":
        branch.setdefault("mode", "auto")
        branch.setdefault("connection_option_id", None)


def next_uid(prefix="b"):
    st.session_state["tree_uid_counter"] += 1
    return f"{prefix}{st.session_state['tree_uid_counter']}"


def used_circuit_ids():
    values = set()
    for branch in branches:
        value = branch.get("circuit_id") or branch.get("feeder_id")
        if value:
            values.add(str(value).strip())
    return values


def next_id(prefix):
    used = used_circuit_ids()
    number = 1
    while f"{prefix}-{number:02d}" in used:
        number += 1
    return f"{prefix}-{number:02d}"


def next_named_id(prefix, key):
    used = {str(branch.get(key, "")).strip() for branch in branches}
    number = 1
    while f"{prefix}-{number:02d}" in used:
        number += 1
    return f"{prefix}-{number:02d}"


def child_branch_uids(parent_uid):
    direct = [b["uid"] for b in branches if b.get("parent_key") == parent_uid]
    result = list(direct)
    for uid in direct:
        result.extend(child_branch_uids(uid))
    return result


def branch_map():
    return {branch["uid"]: branch for branch in branches}


def is_below_sub_board(branch):
    by_uid = branch_map()
    parent_key = branch.get("parent_key", "root")
    seen = set()
    while parent_key != "root":
        if parent_key in seen:
            raise ValueError("branch hierarchy contains a cycle")
        seen.add(parent_key)
        parent = by_uid.get(parent_key)
        if parent is None:
            raise ValueError(f"Branch {branch['uid']} references a missing parent.")
        if parent.get("kind") == "sub_board":
            return True
        parent_key = parent.get("parent_key", "root")
    return False


def final_branch_request(branch):
    phase = branch["phase"]
    voltage = float(voltage_ln if phase == "single" else voltage_ll)
    mode = branch.get("mode", "auto")
    return FinalBranchDesignRequest(
        circuit_id=str(branch["circuit_id"]),
        description=str(branch["description"]),
        mode=mode,
        voltage_v=voltage,
        phase=phase,
        material=branch["material"],
        expected_load_kw=float(branch["load_kw"]) if mode == "auto" else None,
        connection_option_id=branch.get("connection_option_id") if mode == "manual" else None,
        power_factor=float(branch["power_factor"]),
        demand_factor=float(branch["demand_factor"]),
    )


def calculate_branch_previews():
    results = {}
    errors = {}
    for branch in branches:
        if branch.get("kind") != "final":
            continue
        try:
            results[branch["uid"]] = calculate_final_branch(final_branch_request(branch))
        except (TypeError, ValueError) as exc:
            errors[branch["uid"]] = str(exc)
    return results, errors


def build_live_root_request(branch_results):
    circuits = []
    preferences = []
    for branch in branches:
        if branch.get("kind") != "final" or is_below_sub_board(branch):
            continue
        result = branch_results.get(branch["uid"])
        if result is None:
            continue
        circuits.append(result.circuit.request)
        if branch["phase"] == "single" and branch.get("phase_preference", "Auto") in ("L1", "L2", "L3"):
            preferences.append(
                BoardPhasePreference(str(branch["circuit_id"]), branch["phase_preference"])
            )
    if not circuits:
        return None
    return BoardPlanRequest(
        board_id=board_id,
        description=description,
        circuits=tuple(circuits),
        line_to_line_voltage_v=float(voltage_ll),
        line_to_neutral_voltage_v=float(voltage_ln),
        phase_preferences=tuple(preferences),
    )


def build_draft_graph(branch_results):
    graph = make_radial_board_graph(
        board_id=board_id,
        description=description,
        line_to_line_voltage_v=float(voltage_ll),
        line_to_neutral_voltage_v=float(voltage_ln),
    )
    busbar_by_parent_key = {"root": "busbar"}

    for branch in branches:
        uid = branch["uid"]
        parent_key = branch.get("parent_key", "root")
        parent_busbar_id = busbar_by_parent_key.get(parent_key)
        if parent_busbar_id is None:
            raise ValueError(f"Branch {uid} references an unavailable parent hierarchy node.")

        if branch["kind"] == "final":
            mode = branch.get("mode", "auto")
            preview = branch_results.get(uid)
            if mode == "manual" and preview is not None and preview.connection_rating_a is not None:
                display_detail = f"Manual · {preview.connection_rating_a:g} A outlet"
                graph_load_kw = None
            else:
                display_detail = None
                graph_load_kw = float(branch["load_kw"])
            graph = add_radial_circuit(
                graph,
                circuit_id=str(branch["circuit_id"]),
                description=str(branch["description"]),
                load_kw=graph_load_kw,
                phase=branch["phase"],
                power_factor=float(branch["power_factor"]),
                demand_factor=float(branch["demand_factor"]),
                material=branch["material"],
                phase_preference=branch.get("phase_preference", "Auto"),
                display_detail=display_detail,
                parent_busbar_id=parent_busbar_id,
            )
        elif branch["kind"] == "field":
            graph = add_field_feeder(
                graph,
                feeder_id=str(branch["feeder_id"]),
                field_id=str(branch["field_id"]),
                description=str(branch["description"]),
                parent_busbar_id=parent_busbar_id,
            )
            busbar_by_parent_key[uid] = f"{branch['feeder_id']}:{branch['field_id']}:busbar"
        elif branch["kind"] == "sub_board":
            graph = add_sub_board_feeder(
                graph,
                feeder_id=str(branch["feeder_id"]),
                sub_board_id=str(branch["sub_board_id"]),
                description=str(branch["description"]),
                parent_busbar_id=parent_busbar_id,
            )
            busbar_by_parent_key[uid] = f"{branch['feeder_id']}:{branch['sub_board_id']}:busbar"
        else:
            raise ValueError(f"Unsupported branch type: {branch['kind']}")
    return graph


def selected_graph_nodes(selected_node, selected_branch):
    if selected_node in ("source", "incomer", "busbar"):
        return (selected_node,)
    if selected_branch is None:
        return tuple()
    if selected_branch["kind"] == "final":
        return (f"{selected_branch['circuit_id']}:load",)
    if selected_branch["kind"] == "field":
        return (f"{selected_branch['feeder_id']}:{selected_branch['field_id']}:field",)
    return (f"{selected_branch['feeder_id']}:{selected_branch['sub_board_id']}:board",)


def cable_label(result):
    if result.cable_mm2 is None:
        return "—"
    runs = result.cable_runs or 1
    return f"{runs} × {result.cable_mm2:g} mm²" if runs > 1 else f"{result.cable_mm2:g} mm²"


header_left, header_right = st.columns([1, 1])
with header_left:
    board_id = st.text_input("Board ID", value="DB-01", key="tree_board_id")
with header_right:
    description = st.text_input("Board description", value="Distribution board", key="tree_board_description")

with st.expander("Board supply"):
    v1, v2, _ = st.columns([1, 1, 2])
    with v1:
        voltage_ll = st.number_input("Line-line voltage (V)", min_value=1.0, value=400.0, step=5.0, key="tree_vll")
    with v2:
        voltage_ln = st.number_input("Line-neutral voltage (V)", min_value=1.0, value=230.0, step=5.0, key="tree_vln")

node_ids = ["source", "incomer", "busbar"]
labels = {
    "source": "⚡ Supply",
    "incomer": "   └─ Main incomer",
    "busbar": "       └─ Main busbar",
}
token_to_uid = {}
token_to_parent_key = {"busbar": "root"}
children_by_parent = {}
for branch in branches:
    children_by_parent.setdefault(branch.get("parent_key", "root"), []).append(branch)

_GROUP_ICONS = (
    ("🟩", "🟢"),
    ("🟦", "🔵"),
    ("🟪", "🟣"),
    ("🟨", "🟡"),
    ("🟥", "🔴"),
)
group_by_uid = {}
for branch in branches:
    if branch["kind"] in ("field", "sub_board"):
        group_by_uid[branch["uid"]] = len(group_by_uid) % len(_GROUP_ICONS)


def append_tree(parent_key, depth, inherited_group=None):
    siblings = children_by_parent.get(parent_key, [])
    for index, branch in enumerate(siblings):
        uid = branch["uid"]
        last = index == len(siblings) - 1
        stem = "└─" if last else "├─"
        indent = "    " * depth
        own_group = group_by_uid.get(uid, inherited_group)
        if branch["kind"] in ("field", "sub_board"):
            marker = _GROUP_ICONS[own_group][0]
        elif own_group is not None:
            marker = _GROUP_ICONS[own_group][1]
        else:
            marker = "▫️"

        token = f"branch:{uid}"
        if branch["kind"] == "final":
            mode_marker = "A" if branch.get("mode", "auto") == "auto" else "M"
            title = f"{branch['circuit_id']} · {branch['description']} · {mode_marker}"
        elif branch["kind"] == "field":
            title = f"{branch['field_id']} · {branch['description']}"
        else:
            title = f"{branch['sub_board_id']} · {branch['description']}"
        node_ids.append(token)
        labels[token] = f"{indent}{stem} {marker} {title}"
        token_to_uid[token] = uid

        if branch["kind"] in ("field", "sub_board"):
            token_to_parent_key[token] = uid
            append_tree(uid, depth + 1, own_group)


append_tree("root", 3)

pending_selection = st.session_state.pop("tree_next_selected_node", None)
if pending_selection is not None:
    st.session_state["tree_selected_node"] = pending_selection
if st.session_state.get("tree_selected_node", "busbar") not in node_ids:
    st.session_state["tree_selected_node"] = "busbar"

workspace_left, workspace_right = st.columns([0.92, 1.08], gap="large")

with workspace_left:
    st.markdown("### Board structure")
    st.markdown(
        '<div class="tree-note">Select the main busbar, a field, or a sub-board to add below it. A = Auto from load, M = Manual from outlet.</div>',
        unsafe_allow_html=True,
    )

    selected_node = st.radio(
        "Electrical hierarchy",
        node_ids,
        format_func=lambda node_id: labels[node_id],
        label_visibility="collapsed",
        key="tree_selected_node",
    )

    selected_uid = token_to_uid.get(selected_node)
    selected_branch = next((b for b in branches if b["uid"] == selected_uid), None)
    selected_parent_key = token_to_parent_key.get(selected_node)

    add_type_col, add_button_col = st.columns([1.18, 1])
    with add_type_col:
        new_branch_type = st.selectbox(
            "Add under selected",
            ["Final circuit", "Field / circuit group", "Sub-board"],
            disabled=selected_parent_key is None,
            help="A final circuit ends at a consumer. A field groups related circuits. A sub-board creates a separate downstream board.",
        )
    with add_button_col:
        st.write("")
        add_clicked = st.button("＋ Add", disabled=selected_parent_key is None, use_container_width=True)

    if add_clicked:
        uid = next_uid()
        if new_branch_type == "Final circuit":
            branch = {
                "uid": uid,
                "kind": "final",
                "parent_key": selected_parent_key,
                "circuit_id": next_id("C"),
                "description": "New load",
                "mode": "auto",
                "connection_option_id": None,
                "load_kw": 1.0,
                "phase": "single",
                "power_factor": 0.90,
                "demand_factor": 1.00,
                "material": "copper",
                "phase_preference": "Auto",
            }
        elif new_branch_type == "Field / circuit group":
            branch = {
                "uid": uid,
                "kind": "field",
                "parent_key": selected_parent_key,
                "feeder_id": next_id("F"),
                "field_id": next_named_id("FIELD", "field_id"),
                "description": "New field",
            }
        else:
            branch = {
                "uid": uid,
                "kind": "sub_board",
                "parent_key": selected_parent_key,
                "feeder_id": next_id("DBF"),
                "sub_board_id": next_named_id("DB", "sub_board_id"),
                "description": "New sub-board",
            }
        branches.append(branch)
        st.session_state["tree_next_selected_node"] = f"branch:{uid}"
        st.rerun()

    if st.button("Delete selected", disabled=selected_branch is None, use_container_width=True):
        remove_uids = {selected_uid, *child_branch_uids(selected_uid)}
        st.session_state["tree_board_branches"] = [b for b in branches if b["uid"] not in remove_uids]
        st.session_state["tree_next_selected_node"] = "busbar"
        st.rerun()

with workspace_right:
    st.markdown("### Properties")
    st.markdown('<div class="tree-note">Edit the selected object here. Auto/Manual branch sizing updates live.</div>', unsafe_allow_html=True)

    if selected_node == "source":
        with st.container(border=True):
            st.markdown("**Incoming supply**")
            st.write(f"{voltage_ll:g} / {voltage_ln:g} V")
            st.caption("Upstream network and fault-level data will be added later.")
    elif selected_node == "incomer":
        with st.container(border=True):
            st.markdown("**Main incomer · Auto from board demand**")
            st.caption("The live summary below derives a provisional conventional rating from the current root-board phase demand. Full protection verification is not implemented yet.")
    elif selected_node == "busbar":
        with st.container(border=True):
            st.markdown("**Main busbar · Auto**")
            st.caption("Add a final circuit, field or sub-board below this point. Busbar rating remains pending until that engineering model is implemented.")
    elif selected_branch is not None:
        uid = selected_branch["uid"]
        with st.container(border=True):
            if selected_branch["kind"] == "final":
                current_mode = selected_branch.get("mode", "auto")
                mode_label = st.selectbox(
                    "Design mode",
                    ["Auto from load", "Manual from outlet"],
                    index=0 if current_mode == "auto" else 1,
                    key=f"branch_mode_{uid}",
                    help="Auto: enter the consumer load and derive the branch. Manual: select a known outlet rating and design the branch to support it.",
                )
                new_mode = "auto" if mode_label == "Auto from load" else "manual"

                c1, c2 = st.columns(2)
                with c1:
                    new_id = st.text_input("Circuit ID", value=str(selected_branch["circuit_id"]), key=f"branch_id_{uid}")
                with c2:
                    phase_label = st.selectbox(
                        "Phase", ["Single-phase", "Three-phase"],
                        index=0 if selected_branch["phase"] == "single" else 1,
                        key=f"branch_phase_{uid}",
                    )
                new_phase = "single" if phase_label == "Single-phase" else "three"
                new_description = st.text_input("Load / consumer", value=str(selected_branch["description"]), key=f"branch_desc_{uid}")

                new_load = float(selected_branch["load_kw"])
                new_pf = float(selected_branch["power_factor"])
                new_demand = float(selected_branch["demand_factor"])
                new_connection_id = selected_branch.get("connection_option_id")

                if new_mode == "auto":
                    c3, c4 = st.columns(2)
                    with c3:
                        new_load = st.number_input("Expected load (kW)", min_value=0.1, value=float(selected_branch["load_kw"]), step=0.5, key=f"branch_load_{uid}")
                    with c4:
                        new_pf = st.number_input("Power factor", min_value=0.01, max_value=1.0, value=float(selected_branch["power_factor"]), step=0.01, key=f"branch_pf_{uid}")
                    new_demand = st.number_input("Demand factor", min_value=0.01, max_value=1.0, value=float(selected_branch["demand_factor"]), step=0.05, key=f"branch_demand_{uid}")
                    new_connection_id = None
                else:
                    options = connection_options_for_phase(new_phase, include_fixed=False)
                    rated_options = tuple(option for option in options if option.rating_a is not None)
                    option_ids = [option.id for option in rated_options]
                    if not option_ids:
                        st.error("No rated outlet options are available for this phase.")
                        new_connection_id = None
                    else:
                        current_option = selected_branch.get("connection_option_id")
                        if current_option not in option_ids:
                            current_option = option_ids[0]
                        option_by_id = {option.id: option for option in rated_options}
                        new_connection_id = st.selectbox(
                            "Outlet / connection",
                            option_ids,
                            index=option_ids.index(current_option),
                            format_func=lambda option_id: option_by_id[option_id].label,
                            key=f"branch_connection_{uid}",
                        )
                        st.caption("Manual mode treats the selected nominal outlet rating as the required branch current. Demand factor is not applied to that fixed rating.")

                material_label = st.selectbox(
                    "Conductor material", ["Copper", "Aluminium"],
                    index=0 if selected_branch["material"] == "copper" else 1,
                    key=f"branch_material_{uid}",
                )
                new_material = "copper" if material_label == "Copper" else "aluminium"

                phase_preference = "Auto"
                if new_phase == "single":
                    current_preference = selected_branch.get("phase_preference", "Auto")
                    if current_preference not in ("Auto", "L1", "L2", "L3"):
                        current_preference = "Auto"
                    phase_preference = st.selectbox(
                        "Phase assignment", ["Auto", "L1", "L2", "L3"],
                        index=["Auto", "L1", "L2", "L3"].index(current_preference),
                        key=f"branch_lock_{uid}",
                    )

                changed = (
                    new_mode != selected_branch.get("mode", "auto")
                    or new_id.strip() != str(selected_branch["circuit_id"]).strip()
                    or new_description != selected_branch["description"]
                    or float(new_load) != float(selected_branch["load_kw"])
                    or new_phase != selected_branch["phase"]
                    or float(new_pf) != float(selected_branch["power_factor"])
                    or float(new_demand) != float(selected_branch["demand_factor"])
                    or new_material != selected_branch["material"]
                    or new_connection_id != selected_branch.get("connection_option_id")
                    or phase_preference != selected_branch.get("phase_preference", "Auto")
                )
                if changed:
                    selected_branch.update({
                        "mode": new_mode,
                        "circuit_id": new_id.strip(),
                        "description": new_description,
                        "load_kw": float(new_load),
                        "phase": new_phase,
                        "power_factor": float(new_pf),
                        "demand_factor": float(new_demand),
                        "material": new_material,
                        "connection_option_id": new_connection_id if new_mode == "manual" else None,
                        "phase_preference": phase_preference if new_phase == "single" else "Auto",
                    })
                    st.rerun()

                try:
                    branch_preview = calculate_final_branch(final_branch_request(selected_branch))
                    st.markdown('<div class="derived-title">Live derived branch</div>', unsafe_allow_html=True)
                    d1, d2, d3, d4 = st.columns(4)
                    d1.metric("Ib", f"{branch_preview.design_current_a:.1f} A")
                    d2.metric("Breaker", f"{branch_preview.breaker_a:.0f} A" if branch_preview.breaker_a is not None else "—")
                    d3.metric("Cable", cable_label(branch_preview))
                    d4.metric("Outlet", f"{branch_preview.connection_rating_a:.0f} A" if branch_preview.connection_rating_a is not None else "Fixed")
                    if branch_preview.circuit.verification.scope_status != "SUPPORTED_SCOPE":
                        st.caption("Some derived values remain outside the currently verified calculation scope; missing values are intentionally left blank.")
                except (TypeError, ValueError) as exc:
                    st.warning(str(exc))

            elif selected_branch["kind"] == "field":
                st.markdown("**Field / circuit group · Auto from child circuits**")
                c1, c2 = st.columns(2)
                with c1:
                    feeder_id = st.text_input("Field feeder ID", value=str(selected_branch["feeder_id"]), key=f"field_feeder_{uid}")
                with c2:
                    field_id = st.text_input("Field ID", value=str(selected_branch["field_id"]), key=f"field_id_{uid}")
                field_description = st.text_input("Field description", value=str(selected_branch["description"]), key=f"field_desc_{uid}")
                st.caption("Child circuits remain part of this board. Field feeder protection/cable sizing is the next bottom-up aggregation step.")
                if (
                    feeder_id.strip() != str(selected_branch["feeder_id"]).strip()
                    or field_id.strip() != str(selected_branch["field_id"]).strip()
                    or field_description != selected_branch["description"]
                ):
                    selected_branch.update({"feeder_id": feeder_id.strip(), "field_id": field_id.strip(), "description": field_description})
                    st.rerun()
            else:
                st.markdown("**Sub-board · Auto from downstream board**")
                c1, c2 = st.columns(2)
                with c1:
                    feeder_id = st.text_input("Feeder ID", value=str(selected_branch["feeder_id"]), key=f"sub_feeder_{uid}")
                with c2:
                    sub_board_id = st.text_input("Sub-board ID", value=str(selected_branch["sub_board_id"]), key=f"sub_board_id_{uid}")
                sub_description = st.text_input("Sub-board description", value=str(selected_branch["description"]), key=f"sub_desc_{uid}")
                st.caption("A sub-board is a separate calculation boundary. Its demand is not yet propagated into the upstream feeder.")
                if (
                    feeder_id.strip() != str(selected_branch["feeder_id"]).strip()
                    or sub_board_id.strip() != str(selected_branch["sub_board_id"]).strip()
                    or sub_description != selected_branch["description"]
                ):
                    selected_branch.update({"feeder_id": feeder_id.strip(), "sub_board_id": sub_board_id.strip(), "description": sub_description})
                    st.rerun()

branch_results, branch_errors = calculate_branch_previews()
try:
    draft_graph = build_draft_graph(branch_results)
    graph_error = None
except (TypeError, ValueError) as exc:
    draft_graph = None
    graph_error = str(exc)

live_plan = None
live_plan_error = None
try:
    root_request = build_live_root_request(branch_results)
    if root_request is not None:
        live_plan = calculate_board_plan(root_request)
except (TypeError, ValueError) as exc:
    live_plan_error = str(exc)

st.markdown("---")
st.markdown("### Live single-line diagram")
st.markdown('<div class="workflow-note">The diagram and board demand update automatically as you edit. No separate calculate step is required for normal planning.</div>', unsafe_allow_html=True)

if graph_error:
    st.error(graph_error)
elif draft_graph is not None:
    display_graph = draft_graph
    if live_plan is not None:
        display_graph = enrich_graph_with_plan(draft_graph, live_plan)
    highlighted = selected_graph_nodes(selected_node, selected_branch)
    svg = render_board_graph_svg(display_graph, highlighted)
    diagram_html = f'<div style="width:100%;height:650px;display:flex;align-items:center;justify-content:center;overflow:hidden;">{svg}</div>'
    components.html(diagram_html, height=670, scrolling=False)

st.markdown("### Live board summary")
if live_plan_error:
    st.warning(live_plan_error)
elif live_plan is None:
    st.caption("Add a final circuit on this board to start the live board calculation.")
else:
    incomer = live_plan.incomer_candidate
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Provisional incomer", f"{incomer.breaker_rating_a:.0f} A" if incomer.breaker_rating_a is not None else "—")
    m2.metric("L1", f"{live_plan.phase_balance.l1_current_a:.1f} A")
    m3.metric("L2", f"{live_plan.phase_balance.l2_current_a:.1f} A")
    m4.metric("L3", f"{live_plan.phase_balance.l3_current_a:.1f} A")
    m5.metric("Spread", f"{live_plan.phase_balance.spread_a:.1f} A")

    with st.expander("Generated circuit schedule"):
        schedule = []
        mode_by_circuit = {
            str(branch["circuit_id"]): branch.get("mode", "auto")
            for branch in branches if branch.get("kind") == "final"
        }
        for row in live_plan.schedule_rows:
            cable = "—"
            if row.cable_mm2 is not None:
                cable = f"{row.cable_runs} × {row.cable_mm2:g} mm²" if (row.cable_runs or 1) > 1 else f"{row.cable_mm2:g} mm²"
            schedule.append({
                "Circuit": row.circuit_id,
                "Mode": "Manual" if mode_by_circuit.get(row.circuit_id) == "manual" else "Auto",
                "Load / basis": f"{row.load_value:g} A" if row.load_type == "a" else f"{row.load_value:g} kW",
                "Phase": row.assigned_phase,
                "Ib": f"{row.design_current_a:.1f} A",
                "Breaker": f"{row.breaker_a:.0f} A" if row.breaker_a is not None else "—",
                "Cable": cable,
                "Scope": row.scope_status.replace("_", " "),
            })
        st.dataframe(schedule, hide_index=True, use_container_width=True)

    with st.expander("Current calculation scope / checks"):
        st.write(f"• {incomer.basis}")
        st.write("• Automatic phase allocation is a planning heuristic, not an imbalance-compliance check.")
        st.write("• Manual outlet mode fixes the rated outlet current as the branch requirement; it does not invent a consumer load.")
        st.write("• Field feeder aggregation, sub-board feeder demand, busbar rating, selectivity, fault-level checks and final protection verification are not implemented yet.")
        blocking = tuple(c for c in live_plan.circuits if c.verification.blocking_issues)
        for circuit_result in blocking:
            st.markdown(f"**{circuit_result.request.circuit_id} · {circuit_result.request.description}**")
            for issue in circuit_result.verification.blocking_issues:
                st.write(f"• {issue.message}")

if branch_errors:
    with st.expander("Branches needing input"):
        for uid, message in branch_errors.items():
            branch = next((item for item in branches if item["uid"] == uid), None)
            label = branch.get("circuit_id", uid) if branch else uid
            st.write(f"• {label}: {message}")

st.caption("Normal planning is live. A separate full-check action will only be introduced when there are additional explicit checks for it to run.")