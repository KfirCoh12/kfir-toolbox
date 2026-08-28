"""Hierarchy-first board planning UI with a live single-line view."""
import streamlit as st
import streamlit.components.v1 as components

from src.board_graph import (
    add_field_feeder,
    add_radial_circuit,
    add_sub_board_feeder,
    board_plan_request_from_graph,
    enrich_graph_with_plan,
    make_radial_board_graph,
)
from src.board_planner import calculate_board_plan
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
.block-container {max-width: 1500px; padding-top: 1.6rem; padding-bottom: 3rem;}
.hero {padding: 0.5rem 0 1rem 0;}
.hero h1 {margin:0; font-size:2.25rem; letter-spacing:-0.03em;}
.hero p {margin:.45rem 0 0 0; color:#94a3b8; font-size:1rem;}
.eyebrow {font-size:.74rem; font-weight:700; letter-spacing:.11em; text-transform:uppercase; color:#64748b; margin-bottom:.35rem;}
[data-baseweb="select"] > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {border-radius:10px !important;}
[data-testid="stNumberInput"],
[data-testid="stSelectbox"],
[data-testid="stTextInput"] {max-width:280px;}
div.stButton > button {min-height:2.8rem; border-radius:12px; font-weight:700;}
[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stExpander"] {border-radius:12px; border-color:#334155;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px; background:#111827; border-color:#263449;}
[data-testid="stVerticalBlockBorderWrapper"] > div {padding:1rem 1.15rem;}
[data-testid="stMetric"] {background:#111827; border:1px solid #263449; border-radius:14px; padding:.9rem;}
.tree-note {color:#64748b; font-size:.82rem; margin-top:-.35rem;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """<div class="hero"><div class="eyebrow">Electrical engineering · Hierarchy preview</div><h1>⚡ Board Planner</h1><p>Build the electrical hierarchy on the left. The single-line diagram updates from the same model as you work.</p></div>""",
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


def build_draft_graph():
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
            graph = add_radial_circuit(
                graph,
                circuit_id=str(branch["circuit_id"]),
                description=str(branch["description"]),
                load_kw=float(branch["load_kw"]),
                phase=branch["phase"],
                power_factor=float(branch["power_factor"]),
                demand_factor=float(branch["demand_factor"]),
                material=branch["material"],
                phase_preference=branch.get("phase_preference", "Auto"),
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
            busbar_by_parent_key[uid] = (
                f"{branch['feeder_id']}:{branch['field_id']}:busbar"
            )
        elif branch["kind"] == "sub_board":
            graph = add_sub_board_feeder(
                graph,
                feeder_id=str(branch["feeder_id"]),
                sub_board_id=str(branch["sub_board_id"]),
                description=str(branch["description"]),
                parent_busbar_id=parent_busbar_id,
            )
            busbar_by_parent_key[uid] = (
                f"{branch['feeder_id']}:{branch['sub_board_id']}:busbar"
            )
        else:
            raise ValueError(f"Unsupported branch type: {branch['kind']}")
    return graph


def graph_signature():
    return (
        board_id.strip(),
        description.strip(),
        float(voltage_ll),
        float(voltage_ln),
        tuple(tuple(sorted(branch.items())) for branch in branches),
    )


header_left, header_right = st.columns([1, 1])
with header_left:
    board_id = st.text_input("Board ID", value="DB-01", key="tree_board_id")
with header_right:
    description = st.text_input(
        "Board description", value="Distribution board", key="tree_board_description"
    )

with st.expander("Board supply"):
    v1, v2, _ = st.columns([1, 1, 2])
    with v1:
        voltage_ll = st.number_input(
            "Line-line voltage (V)", min_value=1.0, value=400.0, step=5.0, key="tree_vll"
        )
    with v2:
        voltage_ln = st.number_input(
            "Line-neutral voltage (V)", min_value=1.0, value=230.0, step=5.0, key="tree_vln"
        )

left, right = st.columns([0.82, 1.18], gap="large")

with left:
    st.markdown("### Electrical hierarchy")
    st.markdown(
        '<div class="tree-note">Select a busbar to add below it. A branch may end in a final load, a field, or a full sub-board.</div>',
        unsafe_allow_html=True,
    )

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

    def append_tree(parent_key, depth):
        siblings = children_by_parent.get(parent_key, [])
        for index, branch in enumerate(siblings):
            uid = branch["uid"]
            last = index == len(siblings) - 1
            stem = "└─" if last else "├─"
            indent = "    " * depth
            if branch["kind"] == "final":
                cid = str(branch["circuit_id"]).strip() or "?"
                tokens = (
                    (f"branch:{uid}:device", f"{indent}{stem} {cid} · Protection"),
                    (f"branch:{uid}:cable", f"{indent}    └─ Cable"),
                    (f"branch:{uid}:endpoint", f"{indent}        └─ {branch['description']}"),
                )
            elif branch["kind"] == "field":
                fid = str(branch["feeder_id"]).strip() or "?"
                tokens = (
                    (f"branch:{uid}:device", f"{indent}{stem} {fid} · Field protection"),
                    (f"branch:{uid}:cable", f"{indent}    └─ Feeder cable"),
                    (f"branch:{uid}:endpoint", f"{indent}        └─ {branch['description']}"),
                    (f"branch:{uid}:busbar", f"{indent}            └─ {branch['field_id']} busbar"),
                )
            else:
                fid = str(branch["feeder_id"]).strip() or "?"
                tokens = (
                    (f"branch:{uid}:device", f"{indent}{stem} {fid} · Sub-board feeder"),
                    (f"branch:{uid}:cable", f"{indent}    └─ Feeder cable"),
                    (f"branch:{uid}:endpoint", f"{indent}        └─ {branch['description']}"),
                    (f"branch:{uid}:incomer", f"{indent}            └─ {branch['sub_board_id']} incomer"),
                    (f"branch:{uid}:busbar", f"{indent}                └─ {branch['sub_board_id']} busbar"),
                )
            for token, label in tokens:
                node_ids.append(token)
                labels[token] = label
                token_to_uid[token] = uid
            if branch["kind"] in ("field", "sub_board"):
                token_to_parent_key[f"branch:{uid}:busbar"] = uid
                append_tree(uid, depth + 1)

    append_tree("root", 3)

    pending_selection = st.session_state.pop("tree_next_selected_node", None)
    if pending_selection is not None:
        st.session_state["tree_selected_node"] = pending_selection
    if st.session_state.get("tree_selected_node", "busbar") not in node_ids:
        st.session_state["tree_selected_node"] = "busbar"

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

    add_type_col, add_button_col = st.columns([1.15, 1])
    with add_type_col:
        new_branch_type = st.selectbox(
            "Add under selected",
            ["Final circuit", "Field / circuit group", "Sub-board"],
            disabled=selected_parent_key is None,
            help="Select a busbar in the hierarchy, then choose what it feeds.",
        )
    with add_button_col:
        st.write("")
        add_clicked = st.button(
            "＋ Add branch",
            disabled=selected_parent_key is None,
            use_container_width=True,
        )

    if add_clicked:
        uid = next_uid()
        if new_branch_type == "Final circuit":
            branch = {
                "uid": uid,
                "kind": "final",
                "parent_key": selected_parent_key,
                "circuit_id": next_id("C"),
                "description": "New load",
                "load_kw": 1.0,
                "phase": "single",
                "power_factor": 0.90,
                "demand_factor": 1.00,
                "material": "copper",
                "phase_preference": "Auto",
            }
            next_selected = f"branch:{uid}:endpoint"
        elif new_branch_type == "Field / circuit group":
            branch = {
                "uid": uid,
                "kind": "field",
                "parent_key": selected_parent_key,
                "feeder_id": next_id("F"),
                "field_id": next_named_id("FIELD", "field_id"),
                "description": "New field",
            }
            next_selected = f"branch:{uid}:busbar"
        else:
            branch = {
                "uid": uid,
                "kind": "sub_board",
                "parent_key": selected_parent_key,
                "feeder_id": next_id("DBF"),
                "sub_board_id": next_named_id("DB", "sub_board_id"),
                "description": "New sub-board",
            }
            next_selected = f"branch:{uid}:busbar"
        branches.append(branch)
        st.session_state["tree_next_selected_node"] = next_selected
        st.session_state.pop("tree_board_plan", None)
        st.rerun()

    delete_disabled = selected_branch is None
    if st.button(
        "Delete selected branch",
        disabled=delete_disabled,
        use_container_width=True,
    ):
        remove_uids = {selected_uid, *child_branch_uids(selected_uid)}
        st.session_state["tree_board_branches"] = [
            b for b in branches if b["uid"] not in remove_uids
        ]
        st.session_state["tree_next_selected_node"] = "busbar"
        st.session_state.pop("tree_board_plan", None)
        st.rerun()

    st.markdown("### Properties")
    if selected_node == "source":
        with st.container(border=True):
            st.markdown("**Incoming supply**")
            st.write(f"{voltage_ll:g} / {voltage_ln:g} V")
            st.caption("Upstream network and fault-level data will be added later.")
    elif selected_node == "incomer":
        with st.container(border=True):
            st.markdown("**Main incomer · Auto**")
            st.caption("Its rating is derived from downstream board demand when calculation is available. Manual override will be added as a separate mode.")
    elif selected_node == "busbar":
        with st.container(border=True):
            st.markdown("**Main busbar · Auto**")
            st.caption("The board starts here. Add a final circuit, field or sub-board below this busbar.")
    elif selected_branch is not None:
        uid = selected_branch["uid"]
        with st.container(border=True):
            if selected_branch["kind"] == "final":
                c1, c2 = st.columns(2)
                with c1:
                    new_id = st.text_input(
                        "Circuit ID", value=str(selected_branch["circuit_id"]), key=f"branch_id_{uid}"
                    )
                with c2:
                    phase_label = st.selectbox(
                        "Phase",
                        ["Single-phase", "Three-phase"],
                        index=0 if selected_branch["phase"] == "single" else 1,
                        key=f"branch_phase_{uid}",
                    )
                new_phase = "single" if phase_label == "Single-phase" else "three"
                new_description = st.text_input(
                    "Load / consumer",
                    value=str(selected_branch["description"]),
                    key=f"branch_desc_{uid}",
                )
                c3, c4 = st.columns(2)
                with c3:
                    new_load = st.number_input(
                        "Expected load (kW)", min_value=0.1,
                        value=float(selected_branch["load_kw"]), step=0.5,
                        key=f"branch_load_{uid}"
                    )
                with c4:
                    new_pf = st.number_input(
                        "Power factor", min_value=0.01, max_value=1.0,
                        value=float(selected_branch["power_factor"]), step=0.01,
                        key=f"branch_pf_{uid}"
                    )
                c5, c6 = st.columns(2)
                with c5:
                    new_demand = st.number_input(
                        "Demand factor", min_value=0.01, max_value=1.0,
                        value=float(selected_branch["demand_factor"]), step=0.05,
                        key=f"branch_demand_{uid}"
                    )
                with c6:
                    material_label = st.selectbox(
                        "Conductor material", ["Copper", "Aluminium"],
                        index=0 if selected_branch["material"] == "copper" else 1,
                        key=f"branch_material_{uid}"
                    )
                new_material = "copper" if material_label == "Copper" else "aluminium"
                phase_preference = "Auto"
                if new_phase == "single":
                    current_preference = selected_branch.get("phase_preference", "Auto")
                    phase_preference = st.selectbox(
                        "Phase assignment", ["Auto", "L1", "L2", "L3"],
                        index=["Auto", "L1", "L2", "L3"].index(current_preference),
                        key=f"branch_lock_{uid}"
                    )
                changed = (
                    new_id.strip() != str(selected_branch["circuit_id"]).strip()
                    or new_description != selected_branch["description"]
                    or new_load != selected_branch["load_kw"]
                    or new_phase != selected_branch["phase"]
                    or new_pf != selected_branch["power_factor"]
                    or new_demand != selected_branch["demand_factor"]
                    or new_material != selected_branch["material"]
                    or phase_preference != selected_branch.get("phase_preference", "Auto")
                )
                if changed:
                    selected_branch.update({
                        "circuit_id": new_id.strip(),
                        "description": new_description,
                        "load_kw": float(new_load),
                        "phase": new_phase,
                        "power_factor": float(new_pf),
                        "demand_factor": float(new_demand),
                        "material": new_material,
                        "phase_preference": phase_preference if new_phase == "single" else "Auto",
                    })
                    st.session_state.pop("tree_board_plan", None)
                    st.rerun()
            elif selected_branch["kind"] == "field":
                st.markdown("**Field / circuit group · Auto**")
                c1, c2 = st.columns(2)
                with c1:
                    feeder_id = st.text_input(
                        "Field feeder ID", value=str(selected_branch["feeder_id"]), key=f"field_feeder_{uid}"
                    )
                with c2:
                    field_id = st.text_input(
                        "Field ID", value=str(selected_branch["field_id"]), key=f"field_id_{uid}"
                    )
                field_description = st.text_input(
                    "Field description", value=str(selected_branch["description"]), key=f"field_desc_{uid}"
                )
                st.caption("Child circuits contribute to this board. Field feeder aggregation/sizing is still pending and will not be invented.")
                if (
                    feeder_id.strip() != str(selected_branch["feeder_id"]).strip()
                    or field_id.strip() != str(selected_branch["field_id"]).strip()
                    or field_description != selected_branch["description"]
                ):
                    selected_branch.update({
                        "feeder_id": feeder_id.strip(),
                        "field_id": field_id.strip(),
                        "description": field_description,
                    })
                    st.session_state.pop("tree_board_plan", None)
                    st.rerun()
            else:
                st.markdown("**Sub-board feeder · Auto**")
                c1, c2 = st.columns(2)
                with c1:
                    feeder_id = st.text_input(
                        "Feeder ID", value=str(selected_branch["feeder_id"]), key=f"sub_feeder_{uid}"
                    )
                with c2:
                    sub_board_id = st.text_input(
                        "Sub-board ID", value=str(selected_branch["sub_board_id"]), key=f"sub_board_id_{uid}"
                    )
                sub_description = st.text_input(
                    "Sub-board description", value=str(selected_branch["description"]), key=f"sub_desc_{uid}"
                )
                st.caption("A sub-board is a separate calculation boundary. Its demand is not yet propagated into the upstream feeder.")
                if (
                    feeder_id.strip() != str(selected_branch["feeder_id"]).strip()
                    or sub_board_id.strip() != str(selected_branch["sub_board_id"]).strip()
                    or sub_description != selected_branch["description"]
                ):
                    selected_branch.update({
                        "feeder_id": feeder_id.strip(),
                        "sub_board_id": sub_board_id.strip(),
                        "description": sub_description,
                    })
                    st.session_state.pop("tree_board_plan", None)
                    st.rerun()

try:
    draft_graph = build_draft_graph()
    graph_error = None
except (TypeError, ValueError) as exc:
    draft_graph = None
    graph_error = str(exc)

signature = graph_signature()
stored = st.session_state.get("tree_board_plan")
if stored and stored["signature"] != signature:
    st.session_state.pop("tree_board_plan", None)
    stored = None

with right:
    st.markdown("### Live single-line diagram")
    st.caption("The drawing follows the hierarchy immediately. Calculated final-circuit values enrich it after planning.")

    if graph_error:
        st.error(graph_error)
    elif draft_graph is not None:
        display_graph = draft_graph
        if stored:
            display_graph = enrich_graph_with_plan(draft_graph, stored["result"])
        svg = render_board_graph_svg(display_graph)
        height = max(500, min(1000, 350 + len(display_graph.nodes) * 28))
        components.html(svg, height=height, scrolling=True)

    calculate = st.button("Calculate board", type="primary", use_container_width=True)
    if calculate:
        try:
            if draft_graph is None:
                raise ValueError(graph_error or "Board hierarchy is not valid.")
            request = board_plan_request_from_graph(draft_graph)
            result = calculate_board_plan(request)
            st.session_state["tree_board_plan"] = {
                "signature": signature,
                "result": result,
            }
            st.rerun()
        except (TypeError, ValueError) as exc:
            st.session_state.pop("tree_board_plan", None)
            st.error(str(exc))

    if stored:
        result = stored["result"]
        if result.scope_status == "SUPPORTED_SCOPE":
            st.success("Calculated inside the currently supported circuit scope.")
        else:
            st.warning("Some circuit checks remain outside the supported scope; available values are shown without filling the gaps.")

        incomer = result.incomer_candidate
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric(
            "Incomer",
            f"{incomer.breaker_rating_a:.0f} A" if incomer.breaker_rating_a is not None else "—",
        )
        m2.metric("L1", f"{result.phase_balance.l1_current_a:.1f} A")
        m3.metric("L2", f"{result.phase_balance.l2_current_a:.1f} A")
        m4.metric("L3", f"{result.phase_balance.l3_current_a:.1f} A")
        m5.metric("Spread", f"{result.phase_balance.spread_a:.1f} A")

        with st.expander("Generated circuit schedule"):
            schedule = []
            for row in result.schedule_rows:
                cable = "—"
                if row.cable_mm2 is not None:
                    cable = (
                        f"{row.cable_runs} × {row.cable_mm2:g} mm²"
                        if (row.cable_runs or 1) > 1
                        else f"{row.cable_mm2:g} mm²"
                    )
                schedule.append({
                    "Circuit": row.circuit_id,
                    "Load": row.description,
                    "Phase": row.assigned_phase,
                    "Ib": f"{row.design_current_a:.1f} A",
                    "Breaker": f"{row.breaker_a:.0f} A" if row.breaker_a is not None else "—",
                    "Cable": cable,
                    "Scope": row.scope_status.replace("_", " "),
                })
            st.dataframe(schedule, hide_index=True, use_container_width=True)

        blocking = tuple(c for c in result.circuits if c.verification.blocking_issues)
        if blocking:
            with st.expander("Needs verification"):
                for circuit_result in blocking:
                    st.markdown(
                        f"**{circuit_result.request.circuit_id} · {circuit_result.request.description}**"
                    )
                    for issue in circuit_result.verification.blocking_issues:
                        st.write(f"• {issue.message}")

        with st.expander("Board planning assumptions"):
            st.write(f"• {incomer.basis}")
            st.write("• Automatic phase allocation is a planning heuristic, not an imbalance-compliance check.")
            st.write("• Field feeder aggregation, sub-board feeder demand, final incomer protection verification, busbar rating, selectivity and fault-level checks are not implemented yet.")

st.caption(
    "Hierarchy preview: the electrical tree is the source model. Final circuits, fields and sub-boards are generated into the same live SLD."
)
